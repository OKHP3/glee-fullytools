#!/usr/bin/env python3
"""3-way sync for the Cross-Site Foundation Files shared by the three
OverKill Hill P3 sibling sites (overkill-hill, glee-fullytools, askjamie).

Foundation files (must stay byte-identical across all three repos):
    assets/css/theme.css
    assets/js/app.js
    assets/js/mermaid-init.js

Model
-----
This is NOT "OKH is the permanent source of truth, push one-way." It is a
hub topology, with overkill-hill as the hub:

    * A change made in glee-fullytools or askjamie is written into
      overkill-hill (and, once there, out to the *other* sibling too, if
      that sibling is still behind).
    * A change made in overkill-hill is written into BOTH siblings.

In practice this collapses to one rule per file, applied across all three
repos at once: group the three copies of the file by exact byte content.

    * 1 group  -> already in sync. Nothing to do.
    * 2 groups -> the group whose most recent git-log touch of the file is
                  newest is canonical. Every repo NOT already holding that
                  content gets overwritten with it. (This is what produces
                  both directions Jamie asked for -- whichever repo, OKH
                  included, has the freshest edit wins and radiates out to
                  whichever repo(s) don't have it yet.)
    * 3 groups -> genuine three-way conflict (every repo has a different
                  version). This script never guesses at a resolution. It
                  reports all three and stops for a human/agent to decide,
                  the same way earlier phases of this engagement resolved
                  real theme.css conflicts by reading the actual CSS, not
                  by picking "newest" blindly.

Recency is read from `git log -1 --format=%at -- <path>` in each repo (the
commit timestamp of the last commit that touched the file), not filesystem
mtime, which is unreliable across clones/checkouts/OS. If the file has
uncommitted work, the dry-run report marks that source as `dirty` so it is
not mistaken for the previous commit timestamp; write modes stop before
changing files. If a repo has no git history for the file (new/untracked),
filesystem mtime is used as a fallback and the run is flagged so a human can
sanity-check that repo.

Usage
-----
    python3 sync-foundation-files.py                 # dry run (default)
    python3 sync-foundation-files.py --apply          # write files, no commits
    python3 sync-foundation-files.py --commit          # write + git commit per repo
    python3 sync-foundation-files.py --json           # machine-readable report
    python3 sync-foundation-files.py --file theme.css  # limit to one foundation file

Exit codes
----------
    0  everything in sync, or (with --apply/--commit) fully synced+applied
    1  one or more files are in genuine 3-way conflict -- needs a human
    2  a write was applied but a commit could not be made (e.g. another
       process is actively holding that repo's .git/index.lock)
    3  a repo path is missing/not a git checkout -- config problem
    4  dirty local work would be overwritten or mixed into an automated commit

This script is identical across all three sibling repos' scripts/ dirs (the
same pattern as check-csp.py). It locates its siblings relative to its own
path, so it works no matter which of the three checkouts it's run from.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

FOUNDATION_FILES = [
    "assets/css/theme.css",
    "assets/js/app.js",
    "assets/js/mermaid-init.js",
]

# Stable logical repo keys. Discovery accepts the historical lower-case mirror
# names and the default GitHub clone names so the script works on
# case-sensitive and case-insensitive filesystems.
REPO_DIR_CANDIDATES = {
    "overkill-hill": ["overkill-hill", "OverKill-Hill"],
    "glee-fullytools": ["glee-fullytools", "Glee-fullyTools"],
    "askjamie": ["askjamie", "AskJamie"],
}
REPO_DIRS = list(REPO_DIR_CANDIDATES)
STALE_LOCK_SECONDS = 15 * 60

# Repos that need their own downstream housekeeping re-run after a
# foundation file is written into them. Learned the hard way during the
# 2026-08-30 theme.css consolidation: skipping these leaves Glee's cache-bust
# tokens and portfolio stats stale even though the CSS content is correct.
POST_WRITE_HOOKS = {
    "glee-fullytools": {
        "assets/css/theme.css": [
            ["python3", "scripts/sync-css-version.py"],
            ["python3", "scripts/sync-portfolio-stats.py"],
        ],
    },
}


def mirror_root() -> Path:
    # <repo>/scripts/sync-foundation-files.py -> parents[1] is <repo>,
    # parents[2] is the mirror root that holds all three sibling checkouts.
    return Path(__file__).resolve().parents[2]


def discover_repos(root: Path) -> dict[str, Path]:
    repos = {}
    children_by_lower = {
        child.name.lower(): child
        for child in root.iterdir()
        if child.is_dir()
    } if root.is_dir() else {}

    for key, candidates in REPO_DIR_CANDIDATES.items():
        exact = next((root / name for name in candidates if (root / name).is_dir()), None)
        if exact is not None:
            repos[key] = exact
            continue

        folded = next(
            (children_by_lower.get(name.lower()) for name in candidates if name.lower() in children_by_lower),
            None,
        )
        repos[key] = folded if folded is not None else root / candidates[0]
    return repos


def validate_repos(repos: dict[str, Path]) -> list[str]:
    problems = []
    for name, path in repos.items():
        if not path.is_dir():
            problems.append(f"{name}: not found at {path}")
        elif not (path / ".git").exists():
            problems.append(f"{name}: {path} is not a git checkout")
    return problems


def git_last_touch_epoch(repo: Path, relpath: str) -> tuple[int | None, str]:
    """Return (epoch, source) where source is git, dirty, mtime, or missing."""
    try:
        if relpath in git_status_paths(repo, [relpath]):
            return int(time.time()), "dirty"
    except Exception:
        pass

    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%at", "--", relpath],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=20,
        )
        stamp = out.stdout.strip()
        if out.returncode == 0 and stamp:
            return int(stamp), "git"
    except Exception:
        pass
    full = repo / relpath
    if full.exists():
        return int(full.stat().st_mtime), "mtime"
    return None, "missing"


def read_bytes(repo: Path, relpath: str) -> bytes | None:
    full = repo / relpath
    if not full.exists():
        return None
    return full.read_bytes()


def git_status_paths(repo: Path, relpaths: list[str] | None = None) -> set[str]:
    cmd = ["git", "status", "--porcelain=v1"]
    if relpaths:
        cmd.extend(["--", *relpaths])
    out = subprocess.run(
        cmd,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "git status failed")

    changed = set()
    for line in out.stdout.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.add(path)
    return changed


def clear_stale_lock(repo: Path) -> tuple[bool, str]:
    """Move aside only a demonstrably old .git/index.lock.

    A fresh lock may belong to VS Code, Git GUI, GitHub Desktop, or another Git
    process. Removing it would defeat Git's concurrency protection, so this
    function leaves fresh locks in place and reports a commit block instead.
    """
    lock = repo / ".git" / "index.lock"
    if not lock.exists():
        return True, "no lock"

    age = time.time() - lock.stat().st_mtime
    if age < STALE_LOCK_SECONDS:
        return False, (
            f".git/index.lock is {int(age)}s old; refusing to move a possible active Git lock"
        )

    stale = repo / ".git" / f"index.lock.stale-{int(time.time())}"
    try:
        lock.rename(stale)
    except OSError as exc:
        return False, f"could not move stale-looking .git/index.lock: {exc}"
    return True, f"moved stale lock to {stale.name}"


def commit_repo(repo: Path, relpaths: list[str], message: str) -> tuple[bool, str]:
    """Stage exactly relpaths (never -A) and commit. Returns (ok, detail)."""
    lock_ok, lock_detail = clear_stale_lock(repo)
    if not lock_ok:
        return False, lock_detail

    add = subprocess.run(
        ["git", "add", "--"] + relpaths,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if add.returncode != 0:
        return False, f"git add failed: {add.stderr.strip()}"

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=20,
    )
    staged_files = set(staged.stdout.splitlines())
    intended_files = set(relpaths)
    if staged_files != intended_files:
        return False, (
            "refusing to commit: staged set does not match intended set "
            f"(staged={sorted(staged_files)}, intended={sorted(intended_files)})"
        )

    commit = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if commit.returncode != 0:
        stderr = commit.stderr.strip()
        if "index.lock" in stderr:
            return False, "another process is actively holding .git/index.lock; written but not committed"
        return False, f"git commit failed: {stderr}"
    return True, commit.stdout.strip().splitlines()[0] if commit.stdout.strip() else "committed"


def plan_for_file(relpath: str, repos: dict[str, Path]) -> dict:
    contents: dict[str, bytes] = {}
    timestamps: dict[str, tuple[int | None, str]] = {}
    for name, path in repos.items():
        contents[name] = read_bytes(path, relpath)
        timestamps[name] = git_last_touch_epoch(path, relpath)

    missing = [name for name, c in contents.items() if c is None]

    groups: dict[bytes, list[str]] = {}
    for name, c in contents.items():
        if c is None:
            continue
        groups.setdefault(c, []).append(name)

    result = {
        "file": relpath,
        "missing_in": missing,
        "timestamps": {n: t for n, t in timestamps.items()},
        "status": None,
        "writes": [],  # list of {repo, bytes, source_repo}
        "conflict_groups": None,
    }

    if len(groups) <= 1 and not missing:
        result["status"] = "in-sync"
        return result

    if len(groups) >= 3:
        result["status"] = "conflict"
        result["conflict_groups"] = [
            {
                "repos": members,
                "size": len(content),
                "newest_touch": max(
                    (timestamps[m][0] for m in members if timestamps[m][0] is not None),
                    default=None,
                ),
            }
            for content, members in groups.items()
        ]
        return result

    # 2 (or 1-with-missing) groups: pick the group with the newest touch.
    def group_newest(members: list[str]) -> int:
        stamps = [timestamps[m][0] for m in members if timestamps[m][0] is not None]
        return max(stamps) if stamps else -1

    ranked = sorted(groups.items(), key=lambda kv: group_newest(kv[1]), reverse=True)
    winning_content, winning_members = ranked[0]

    # Deterministic tie-break: if two groups tie on newest touch, prefer
    # whichever group overkill-hill belongs to (it's the hub of reference).
    if len(ranked) > 1 and group_newest(winning_members) == group_newest(ranked[1][1]):
        if "overkill-hill" not in winning_members and "overkill-hill" in ranked[1][1]:
            winning_content, winning_members = ranked[1]

    source_repo = max(
        winning_members,
        key=lambda m: (timestamps[m][0] if timestamps[m][0] is not None else -1),
    )

    result["status"] = "sync-needed"
    result["winning_repos"] = winning_members
    result["source_repo"] = source_repo
    for name in repos:
        if name in winning_members:
            continue
        result["writes"].append({
            "repo": name,
            "bytes": len(winning_content),
            "source_repo": source_repo,
            "content": winning_content,
        })
    return result


def format_ts(epoch: int | None) -> str:
    if epoch is None:
        return "unknown"
    return time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(epoch))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write resolved content to disk (no git commit)")
    ap.add_argument("--commit", action="store_true", help="write and git commit in each changed repo (implies --apply)")
    ap.add_argument("--no-hooks", action="store_true", help="skip POST_WRITE_HOOKS (sync-css-version.py etc.) after writes")
    ap.add_argument("--file", action="append", dest="files", help="limit to this foundation file (basename or relpath); repeatable")
    ap.add_argument("--json", action="store_true", help="print a machine-readable report instead of text")
    args = ap.parse_args()

    apply_writes = args.apply or args.commit

    root = mirror_root()
    repos = discover_repos(root)
    problems = validate_repos(repos)
    if problems:
        if args.json:
            print(json.dumps({"error": "invalid repo config", "problems": problems}, indent=2))
        else:
            print("Cannot proceed -- repo configuration problem(s):")
            for p in problems:
                print(f"  - {p}")
        return 3

    target_files = FOUNDATION_FILES
    if args.files:
        wanted = set(args.files)
        target_files = [f for f in FOUNDATION_FILES if f in wanted or Path(f).name in wanted]
        if not target_files:
            print(f"--file matched nothing in {FOUNDATION_FILES}", file=sys.stderr)
            return 3

    plans = [plan_for_file(f, repos) for f in target_files]

    had_conflict = False
    had_lock_block = False
    had_dirty_block = False
    had_hook_failure = False
    writes_by_repo: dict[str, list[str]] = {}
    hook_failures: list[dict[str, str]] = []

    if apply_writes:
        dirty_checks: dict[str, set[str]] = {}
        for repo_name, repo_path in repos.items():
            relpaths = None if args.commit else target_files
            dirty = git_status_paths(repo_path, relpaths)
            if dirty:
                dirty_checks[repo_name] = dirty

        if dirty_checks:
            had_dirty_block = True
            if args.json:
                print(json.dumps({
                    "error": "dirty worktree would be overwritten or mixed into an automated commit",
                    "dirty": {name: sorted(paths) for name, paths in dirty_checks.items()},
                }, indent=2))
            else:
                print("Cannot proceed -- dirty local work needs review before automated sync:")
                for name, paths in dirty_checks.items():
                    scope = "worktree" if args.commit else "foundation file(s)"
                    print(f"  - {name}: dirty {scope}: {', '.join(sorted(paths))}")
            return 4

    for plan in plans:
        if plan["status"] == "conflict":
            had_conflict = True
            continue
        if plan["status"] != "sync-needed":
            continue
        for w in plan["writes"]:
            repo_path = repos[w["repo"]]
            if apply_writes:
                (repo_path / plan["file"]).write_bytes(w["content"])
                writes_by_repo.setdefault(w["repo"], []).append(plan["file"])
                if not args.no_hooks:
                    for hook in POST_WRITE_HOOKS.get(w["repo"], {}).get(plan["file"], []):
                        hook_result = subprocess.run(
                            hook,
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            timeout=60,
                        )
                        if hook_result.returncode != 0:
                            had_hook_failure = True
                            hook_failures.append({
                                "repo": w["repo"],
                                "file": plan["file"],
                                "hook": " ".join(hook),
                                "stderr": hook_result.stderr.strip(),
                                "stdout": hook_result.stdout.strip(),
                            })
                            continue
                        if args.commit:
                            for changed in git_status_paths(repo_path):
                                writes_by_repo.setdefault(w["repo"], [])
                                if changed not in writes_by_repo[w["repo"]]:
                                    writes_by_repo[w["repo"]].append(changed)
            # content no longer needed after writing/reporting; drop it so
            # the JSON report below doesn't dump raw file bytes
            w.pop("content", None)

    commit_results = {}
    if args.commit:
        for repo_name, relpaths in writes_by_repo.items():
            file_list = ", ".join(Path(p).name for p in relpaths)
            message = (
                f"Sync foundation files from {plans[0].get('source_repo', 'sibling')} "
                f"via sync-foundation-files.py ({file_list})"
            )
            ok, detail = commit_repo(repos[repo_name], relpaths, message)
            commit_results[repo_name] = {"ok": ok, "detail": detail}
            if not ok:
                had_lock_block = True

    if args.json:
        files_report = [dict(plan) for plan in plans]
        out = {
            "mirror_root": str(root),
            "mode": "commit" if args.commit else ("apply" if args.apply else "dry-run"),
            "files": files_report,
            "writes_by_repo": writes_by_repo,
            "commit_results": commit_results,
            "hook_failures": hook_failures,
        }
        print(json.dumps(out, indent=2, default=str))
    else:
        mode = "COMMIT" if args.commit else ("APPLY" if args.apply else "DRY RUN")
        print(f"sync-foundation-files.py -- mode: {mode}")
        print(f"mirror root: {root}\n")
        for plan in plans:
            print(f"== {plan['file']} ==")
            for name in REPO_DIRS:
                ts, src = plan["timestamps"].get(name, (None, "missing"))
                marker = " (fallback: fs mtime, no git history)" if src == "mtime" else ""
                print(f"  {name:<18} last touch: {format_ts(ts)}{marker}")
            if plan["missing_in"]:
                print(f"  MISSING in: {', '.join(plan['missing_in'])}")
            if plan["status"] == "in-sync":
                print("  status: in sync, nothing to do\n")
                continue
            if plan["status"] == "conflict":
                print("  status: CONFLICT -- three different versions, needs manual/agent review")
                for g in plan["conflict_groups"]:
                    print(f"    - held by {', '.join(g['repos'])}: {g['size']} bytes, newest touch {format_ts(g['newest_touch'])}")
                print()
                continue
            print(f"  status: sync needed -- canonical source: {plan['source_repo']} (held also by {', '.join(plan['winning_repos'])})")
            for w in plan["writes"]:
                verb = "wrote" if apply_writes else "would write"
                print(f"    {verb} {w['bytes']} bytes to {w['repo']}/{plan['file']} (from {w['source_repo']})")
            print()

        if args.commit:
            print("-- commits --")
            for name, res in commit_results.items():
                status = "OK" if res["ok"] else "BLOCKED"
                print(f"  {name}: {status} -- {res['detail']}")
            print()

        if hook_failures:
            print("-- post-write hook failures --")
            for failure in hook_failures:
                print(f"  {failure['repo']}: {failure['hook']} failed for {failure['file']}")
                detail = failure["stderr"] or failure["stdout"] or "no output"
                print(f"    {detail}")
            print()

        if not apply_writes and any(p["status"] == "sync-needed" for p in plans):
            print("Dry run only. Re-run with --apply to write files, or --commit to also commit per repo.")

    if had_conflict:
        return 1
    if had_lock_block:
        return 2
    if had_hook_failure:
        return 2
    if had_dirty_block:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
