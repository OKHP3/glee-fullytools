#!/usr/bin/env python3
"""Inventory declared technology versions and check authoritative release feeds.

Standard library only. Writes reports, never installs packages or edits pins.
Exit 2 means incomplete upstream evidence; --fail-on-updates also exits 1 for
newer direct dependencies or runtimes. Indirect upgrades belong to their parent.
"""
from __future__ import annotations

import argparse
import gzip
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STABLE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)$")
NODE_FEED = "https://nodejs.org/dist/index.json"
PYTHON_FEED = "https://www.python.org/downloads/"


def version(value):
    match = STABLE.fullmatch(str(value))
    if not match:
        raise ValueError(f"Not a stable X.Y.Z release: {value!r}")
    return tuple(map(int, match.groups()))


def comparison(current, latest):
    target = version(latest)
    if re.fullmatch(r"v?\d+(?:\.\d+)?", current):
        prefix = tuple(map(int, current.lstrip("v").split(".")))
        return "newer-line" if target[:len(prefix)] > prefix else "floating-selector"
    try:
        actual = version(current)
    except ValueError:
        return "unresolved-current"
    return "update" if target > actual else "current" if target == actual else "ahead-review"


def row(name, kind, current, evidence, source, scope="direct"):
    return dict(name=name, kind=kind, current=current, evidence=evidence,
                source=source, scope=scope)


def inventory(root):
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    direct = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    rows = []
    for path, item in lock["packages"].items():
        if not path or "version" not in item:
            continue
        name = path.rsplit("node_modules/", 1)[-1]
        is_direct = path == f"node_modules/{name}" and name in direct
        rows.append(row(name, "npm", item["version"], f"package-lock.json: {path}",
                        f"https://registry.npmjs.org/{urllib.parse.quote(name, safe='')}/latest",
                        "direct" if is_direct else "transitive"))
    for name, pin in direct.items():
        if lock["packages"].get(f"node_modules/{name}", {}).get("version") != pin:
            raise ValueError(f"Manifest/lock disagreement for {name}")
    for name, pin in re.findall(r"^([\w.-]+)==([^\s#]+)",
                                (root / "requirements-qa.txt").read_text(), re.M):
        rows.append(row(name, "pypi", pin, "requirements-qa.txt",
                        f"https://pypi.org/pypi/{name}/json"))
    # These are the non-extra dependencies of the two Python QA packages.
    # No Python lock exists, so do not claim a CI-resolved version for them.
    for name in ("soupsieve", "typing-extensions", "pyee", "greenlet"):
        rows.append(row(name, "pypi", "not locked", "requirements-qa.txt has no transitive lock",
                        f"https://pypi.org/pypi/{name}/json", "transitive-unlocked"))
    node = (root / ".node-version").read_text().strip()
    rows.append(row("Node.js", "node", node, ".node-version; package.json engines", NODE_FEED))
    rows.append(row("npm bundled with pinned Node", "npm-bundled", "derived from Node release",
                    ".node-version; no packageManager pin", "https://registry.npmjs.org/npm/latest"))
    workflows = sorted((root / ".github/workflows").glob("*.y*ml"))
    actions = {}
    pythons = {}
    for path in workflows:
        text = path.read_text(encoding="utf-8")
        for name, pin in re.findall(r"^\s*(?:-\s*)?uses:\s*([\w.-]+/[\w.-]+)@([^\s#]+)", text, re.M):
            actions.setdefault((name, pin), []).append(path.relative_to(root).as_posix())
        for pin in re.findall(r"python-version:\s*['\"]?([\d.]+)", text):
            pythons.setdefault(pin, []).append(path.relative_to(root).as_posix())
    for (name, pin), paths in sorted(actions.items()):
        rows.append(row(name, "action", pin, "; ".join(sorted(set(paths))),
                        f"https://api.github.com/repos/{name}/releases/latest"))
    for pin, paths in sorted(pythons.items()):
        rows.append(row("Python CI", "python", pin, "; ".join(sorted(set(paths))), PYTHON_FEED))
    replit = (root / ".replit").read_text()
    for kind, pin in re.findall(r'"(nodejs|python)-([\d.]+)"', replit):
        rows.append(row(f"Replit {kind}", "node" if kind == "nodejs" else "python",
                        pin, ".replit module selector; remote patch unknown",
                        NODE_FEED if kind == "nodejs" else PYTHON_FEED))
    rows.append(row("Mermaid", "npm", (root / "assets/vendor/mermaid/VERSION").read_text().strip(),
                    "assets/vendor/mermaid/VERSION", "https://registry.npmjs.org/mermaid/latest", "vendored"))
    return rows


def fetch(url):
    headers = {"User-Agent": "glee-fully-technology-review", "Accept": "application/json"}
    # Never send a GitHub credential to registries or other hosts.
    if urllib.parse.urlparse(url).hostname == "api.github.com" and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=25) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        text = body.decode("utf-8")
    return text if url == PYTHON_FEED else json.loads(text)


def resolve(item, payloads, node_pin):
    data = payloads[item["source"]]
    if isinstance(data, Exception):
        raise ValueError(str(data))
    kind = item["kind"]
    if kind == "node":
        stable = [x for x in data if STABLE.fullmatch(x["version"])]
        latest = max(stable, key=lambda x: version(x["version"]))["version"].lstrip("v")
        item["latest_lts"] = max((x for x in stable if x["lts"]), key=lambda x: version(x["version"]))["version"].lstrip("v")
        item["update_target"] = item["latest_lts"]
        major = int(item["current"].split(".")[0])
        item["latest_same_major"] = max((x for x in stable if version(x["version"])[0] == major), key=lambda x: version(x["version"]))["version"].lstrip("v")
    elif kind == "python":
        releases = set(re.findall(r"Python (\d+\.\d+\.\d+)(?=[\s<])", data))
        latest = max(releases, key=version)
    elif kind == "action":
        if data.get("prerelease") or data.get("draft"):
            raise ValueError("Upstream returned a prerelease or draft")
        latest = data["tag_name"].lstrip("v")
    elif kind == "pypi":
        stable = [v for v, files in data["releases"].items()
                  if STABLE.fullmatch(v) and any(not f.get("yanked", False) for f in files)]
        latest = max(stable, key=version)
    else:
        latest = data["version"]
        if kind == "npm-bundled":
            nodes = payloads[NODE_FEED]
            if isinstance(nodes, Exception):
                raise ValueError(str(nodes))
            item["current"] = next(x["npm"] for x in nodes if x["version"] == f"v{node_pin}")
        if data.get("engines"):
            item["latest_engines"] = data["engines"]
    version(latest)  # Reject prereleases and malformed metadata, never guess.
    item["latest_stable"] = latest
    item["status"] = comparison(item["current"], item.get("update_target", latest))


def check(rows, node_pin, fetcher=fetch):
    urls = sorted({x["source"] for x in rows} | {NODE_FEED})
    def safe_fetch(url):
        try:
            return url, fetcher(url)
        except Exception as error:
            return url, error
    with ThreadPoolExecutor(max_workers=6) as pool:
        payloads = dict(pool.map(safe_fetch, urls))
    for item in rows:
        try:
            resolve(item, payloads, node_pin)
        except (ValueError, KeyError, TypeError, StopIteration) as error:
            item.update(status="unknown", latest_stable=None, error=str(error))
    return rows


def markdown(report):
    lines = ["# Technology version register", "", f"Retrieved: {report['retrieved_at']}",
             f"Source commit: `{report['source_commit']}` (working tree may contain changes).", "",
             "Generated by `scripts/technology-versions.py`. See `docs/technology-update-plan.md`",
             "for standards, services, environment evidence, and the upgrade process.", "",
             "A latest release is an upgrade candidate, not a compatibility result. Floating",
             "selectors do not prove the exact version used by an earlier CI run.",
             "Node update results track latest LTS; latest stable Current is also reported.", ""]
    for title, transitive in (("Direct technologies and runtime selectors", False), ("Indirect packages", True)):
        lines += ["", f"## {title}", "", "| Technology | Current / selected | Latest stable | Result | Evidence and source |",
                  "|---|---|---|---|---|"]
        for item in report["technologies"]:
            if item["scope"].startswith("transitive") != transitive:
                continue
            details = item["evidence"].replace("|", "\\|")
            extra = f"; LTS {item['latest_lts']}" if "latest_lts" in item else ""
            lines.append(f"| {item['name']} ({item['kind']}) | {item['current']} | {item.get('latest_stable') or 'UNKNOWN'}{extra} | {item['status']} | {details}; [release feed]({item['source']}) |")
    errors = [x for x in report["technologies"] if x["status"] == "unknown"]
    if errors:
        lines += ["", "## Incomplete checks", ""] + [f"- {x['name']}: {x['error']}" for x in errors]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--fail-on-updates", action="store_true")
    args = parser.parse_args()
    rows = check(inventory(ROOT), (ROOT / ".node-version").read_text().strip())
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report = dict(retrieved_at=datetime.now(timezone.utc).isoformat(), source_commit=commit, technologies=rows)
    for path, content in ((args.json, json.dumps(report, indent=2) + "\n"), (args.markdown, markdown(report))):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    errors = sum(x["status"] == "unknown" for x in rows)
    updates = sum(x["status"] in ("update", "newer-line") and not x["scope"].startswith("transitive") for x in rows)
    print(f"Checked {len(rows)} records: {updates} direct update candidates, {errors} incomplete checks.")
    return 2 if errors else 1 if args.fail_on_updates and updates else 0


if __name__ == "__main__":
    raise SystemExit(main())
