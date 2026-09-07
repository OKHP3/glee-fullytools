#!/usr/bin/env python3
"""Stage and verify the reviewed Pages public inventory, including transfer checks.

Only this allowlisted staging directory may use upload-artifact's hidden-file
option. Verification compares its complete file set and bytes with the exact
release checkout, then checks first-party page, sitemap, and runtime references.
No dependencies, recursive deletion, source changes, or publication are needed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tarfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT_FILES = {
    "index.html", "404.html", "offline.html", "under-construction.html",
    "CNAME", ".nojekyll", "favicon.ico", "robots.txt", "humans.txt", "llms.txt",
    "sitemap.xml", "feed.xml", "site.webmanifest", "sw.js", "_headers",
}
PAGE_DIRS = {"about", "arcade", "contact", "ecosystem", "foundry", "legal", "persona",
             "search", "showcase", "toolbox", "universe"}
DATA_FILES = {"search-index.json", "sparkle.json", "icon-map.json", "universe-map.json"}
IMAGE_EXTENSIONS = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".avif"}
# Add a specific filename only when it becomes an intentional visitor download.
DOWNLOAD_FILES: set[str] = set()
ORIGIN = "https://glee-fully.tools"
PROVENANCE = "release-provenance.json"


def is_public(name: str) -> bool:
    path = PurePosixPath(name)
    if name in ROOT_FILES or name == ".well-known/security.txt":
        return True
    if any(part.startswith(".") for part in path.parts):
        return False
    if path.parts[0] in PAGE_DIRS:
        return path.suffix == ".html"
    if len(path.parts) < 3 or path.parts[0] != "assets":
        return False
    family = path.parts[1]
    if family == "css":
        return path.suffix == ".css"
    if family == "js":
        return path.suffix == ".js"
    if family == "data":
        return len(path.parts) == 3 and path.name in DATA_FILES
    if family == "img":
        return path.suffix.lower() in IMAGE_EXTENSIONS
    if family == "vendor":
        return (path.parts[2] == "mermaid" and
                (path.suffix in {".mjs", ".js"} or path.name in {"LICENSE", "VERSION"}))
    if family == "downloads":
        return name in DOWNLOAD_FILES
    return False


def safe_path(path: Path, root: Path) -> None:
    """Reject symlinks and Windows junction/reparse points before reading."""
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError(f"link or reparse point is not allowed: {path}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"path escapes artifact boundary: {path}")


def files_below(root: Path):
    safe_path(root, root)
    for directory, directories, filenames in os.walk(root, followlinks=False):
        for name in directories + filenames:
            safe_path(Path(directory) / name, root)
        for name in filenames:
            yield Path(directory) / name


def inventory(source: Path) -> set[str]:
    result = set()
    for name in ROOT_FILES | {".well-known/security.txt"}:
        path = source / name
        if not path.exists():
            raise ValueError(f"required public file missing: {name}")
        for parent in path.parents:
            if parent == source:
                break
            safe_path(parent, source)
        safe_path(path, source)
        result.add(name)
    for name in sorted(PAGE_DIRS | {"assets/css", "assets/js", "assets/data", "assets/img",
                                    "assets/vendor/mermaid", "assets/downloads"}):
        directory = source / name
        if directory.exists():
            # Check every ancestor as well as the leaf, including assets/.
            for parent in directory.parents:
                if parent == source:
                    break
                safe_path(parent, source)
            for path in files_below(directory):
                relative = path.relative_to(source).as_posix()
                if is_public(relative):
                    result.add(relative)
    return result


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        for key in ("href", "src", "poster", "data-src"):
            if attrs.get(key):
                self.urls.append(attrs[key])
        for entry in attrs.get("srcset", "").split(","):
            if entry.strip():
                self.urls.append(entry.strip().split()[0])
        if tag == "meta" and attrs.get("property") in {"og:image", "og:url"}:
            self.urls.append(attrs.get("content", ""))
        if tag == "meta" and attrs.get("name") == "twitter:image":
            self.urls.append(attrs.get("content", ""))


def check_references(output: Path, names: set[str]) -> None:
    missing = set()
    html_text = "\n".join((output / name).read_text(encoding="utf-8")
                          for name in names if name.endswith(".html"))
    # The shared runtime contains branches for sibling sites. They are inactive
    # in this Glee-only, English public tree; require them if a matching page is added.
    inactive = set()
    if not re.search(r'''<html\b[^>]*\blang=['"]fr(?:[-'"])''', html_text, re.I):
        inactive.add("/assets/data/search-index.fr.json")
    if not re.search(r'''<body\b[^>]*\bclass=['"][^'"]*\baskjamie-main\b''', html_text, re.I):
        inactive.add("/assets/js/askjamie-analytics.js")

    def require(value: str, source: str):
        if not value or value.startswith("#"):
            return
        url = urlsplit(urljoin(ORIGIN + "/" + source, value))
        if url.scheme not in {"http", "https"} or url.netloc != urlsplit(ORIGIN).netloc:
            return
        relative = unquote(url.path).lstrip("/")
        if not relative or relative.endswith("/"):
            relative += "index.html"
        if relative not in names and relative.rstrip("/") + "/index.html" not in names:
            missing.add(f"{source}: {value}")

    for name in sorted(names):
        path = output / name
        if name.endswith(".html"):
            parser = References()
            parser.feed(path.read_text(encoding="utf-8"))
            for value in parser.urls:
                require(value, name)
        elif name.endswith(".css"):
            for value in re.findall(r"url\(\s*['\"]?([^)'\"]+)", path.read_text(encoding="utf-8")):
                require(value.strip(), name)
        elif name.endswith((".js", ".mjs")):
            text = path.read_text(encoding="utf-8")
            # Literal static/dynamic imports and the adapter/data paths loaded by JS.
            for value in re.findall(r'''(?:\bfrom\s*|\bimport\s*\(?)['"]((?:\.{1,2}/|/|https?://)[^'"]+)['"]''', text):
                require(value, name)
            for value in re.findall(r'''['"](/assets/[^'"\s]+)['"]''', text):
                if name != "assets/js/app.js" or value not in inactive:
                    require(value, name)
    for item in ET.parse(output / "sitemap.xml").iter():
        if item.tag.rsplit("}", 1)[-1] == "loc" and item.text:
            require(item.text, "sitemap.xml")
    manifest = json.loads((output / "site.webmanifest").read_text(encoding="utf-8"))
    for icon in manifest.get("icons", []):
        require(icon["src"], "site.webmanifest")
    worker = (output / "sw.js").read_text(encoding="utf-8")
    precache = re.search(r"const PRECACHE_URLS\s*=\s*\[(.*?)\];", worker, re.S)
    if not precache:
        raise ValueError("service-worker precache declaration missing")
    for value in re.findall(r'''['"]([^'"]+)['"]''', precache.group(1)):
        require(value, "sw.js")
    search = output / "assets/data/search-index.json"
    if search.is_file():
        data = json.loads(search.read_text(encoding="utf-8"))
        entries = data if isinstance(data, list) else data.get("pages", data.get("items", []))
        for entry in entries:
            require(entry.get("url", ""), "assets/data/search-index.json")
    if missing:
        raise ValueError("missing staged public references:\n" + "\n".join(sorted(missing)))


def verify(source: Path, output: Path, commit: str) -> dict:
    expected = inventory(source)
    actual = {path.relative_to(output).as_posix() for path in files_below(output)}
    expected_dirs = {parent.as_posix() for name in expected for parent in PurePosixPath(name).parents
                     if parent.as_posix() != "."}
    for directory, directories, _ in os.walk(output, followlinks=False):
        for name in directories:
            relative = (Path(directory) / name).relative_to(output).as_posix()
            if relative not in expected_dirs:
                raise ValueError(f"unexpected artifact directory: {relative}")
    if actual != expected | {PROVENANCE}:
        raise ValueError(f"artifact inventory mismatch; missing={sorted((expected | {PROVENANCE}) - actual)}; "
                         f"unexpected={sorted(actual - expected - {PROVENANCE})}")
    for name in sorted(expected):
        if hashlib.sha256((source / name).read_bytes()).digest() != hashlib.sha256((output / name).read_bytes()).digest():
            raise ValueError(f"artifact bytes differ from release checkout: {name}")
    provenance = json.loads((output / PROVENANCE).read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or provenance.get("commit") != commit:
        raise ValueError("artifact provenance commit does not match release commit")
    if (output / "CNAME").read_text(encoding="utf-8").strip() != "glee-fully.tools":
        raise ValueError("unexpected artifact custom domain")
    if not (output / ".well-known/security.txt").stat().st_size:
        raise ValueError("security.txt is empty")
    check_references(output, actual)
    return {"commit": commit, "files": len(actual),
            "html_pages": sum(name.endswith(".html") for name in actual),
            "bytes": sum((output / name).stat().st_size for name in actual),
            "hidden_public_files": [".nojekyll", ".well-known/security.txt"]}


def stage(source: Path, output: Path, provenance: dict) -> dict:
    source, output = source.resolve(), output.absolute()
    if output.resolve().is_relative_to(source):
        raise ValueError("staging directory must be outside the source checkout")
    if output.exists():
        safe_path(output, output)
        if any(output.iterdir()):
            raise ValueError("staging directory must be empty; existing content is never deleted")
    else:
        output.mkdir(parents=True)
    for name in sorted(inventory(source)):
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, destination)
    (output / PROVENANCE).write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return verify(source, output, provenance.get("commit", ""))


def verify_tar(source: Path, output: Path, commit: str, archive: Path) -> dict:
    """Check the actual Pages tar without extracting or trusting member paths."""
    result = verify(source, output, commit)
    expected = inventory(source) | {PROVENANCE}
    expected_dirs = {parent.as_posix() for name in expected for parent in PurePosixPath(name).parents}
    seen = set()
    with tarfile.open(archive, "r:*") as package:
        for member in package:
            name = member.name
            while name.startswith("./"):
                name = name[2:]
            member_path = PurePosixPath(name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"unsafe Pages archive member: {member.name}")
            if member.isdir():
                if member_path.as_posix() not in expected_dirs:
                    raise ValueError(f"unexpected Pages archive directory: {member.name}")
                continue
            if not member.isfile():
                raise ValueError(f"unsafe Pages archive member: {member.name}")
            if name not in expected or name in seen:
                raise ValueError(f"unexpected or duplicate Pages archive member: {name}")
            with package.extractfile(member) as content:
                if hashlib.sha256(content.read()).digest() != hashlib.sha256((output / name).read_bytes()).digest():
                    raise ValueError(f"Pages archive bytes differ: {name}")
            seen.add(name)
    if seen != expected:
        raise ValueError(f"Pages archive missing files: {sorted(expected - seen)}")
    return result | {"pages_archive_verified": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["stage", "verify", "verify-tar"])
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    provenance = {"repository": os.environ.get("GITHUB_REPOSITORY", "OKHP3/Glee-fullyTools"),
                  "commit": args.commit, "ref": os.environ.get("GITHUB_REF", "local"),
                  "event": os.environ.get("GITHUB_EVENT_NAME", "local-validation"),
                  "workflow_run": os.environ.get("GITHUB_RUN_ID", "local")}
    try:
        if args.command == "stage":
            result = stage(args.source, args.output, provenance)
        elif args.command == "verify-tar":
            if not args.archive:
                raise ValueError("--archive is required for verify-tar")
            result = verify_tar(args.source, args.output, args.commit, args.archive)
        else:
            result = verify(args.source, args.output, args.commit)
    except (ValueError, OSError, ET.ParseError, tarfile.TarError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
