#!/usr/bin/env python3
"""
push-to-github.py
-----------------
Pushes unified governance files to all three OKHP3 repos via the GitHub API.

Usage:
    GITHUB_TOKEN=<pat> python3 scripts/push-to-github.py [--dry-run]

The PAT needs: repo (read + write contents) scope on all three repos.

Sync manifest (as of 2026-05-29):
    AGENTS.md                      -- all three repos (brand-specific sections differ)
    .editorconfig                  -- all three repos (identical)
    .github/copilot-instructions.md -- all three repos (identical)
    .github/workflows/validate.yml  -- all three repos (Glee variant includes accent-contrast step)
"""

import base64
import json
import os
import sys
import urllib.request
import urllib.error

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
COMMITTER = {
    "name": "OKHP3 Sync Bot",
    "email": "contact@overkillhill.com",
}

# ---------------------------------------------------------------------------
# Inline content for files that are generated at sync time rather than
# read from local paths. Keeps the script self-contained.
# ---------------------------------------------------------------------------

EDITORCONFIG = """\
# EditorConfig -- https://editorconfig.org
# Aligned with 2025/2026 web defaults: UTF-8, LF, final newline, no
# trailing whitespace. Per-language indentation matches the existing
# codebase.

root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.py]
indent_size = 4

[*.md]
# Markdown is whitespace-sensitive (hard line breaks) -- keep trailing
# spaces intact.
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
"""

COPILOT_INSTRUCTIONS = """\
# Copilot instructions

## Goals
- Optimize for correctness, clarity, and maintainability.
- Prefer small, reviewable commits over big rewrites.

## How to respond
- Start with a 3-6 step plan.
- Then show the code changes.
- Then show how to run / test.

## Coding conventions
- Follow existing project structure and naming.
- Prefer pure functions and clear boundaries.
- Do not introduce new dependencies unless necessary (and explain why).

## Safety
- Never print, log, or hardcode secrets.
- Use environment variables for credentials.
- Validate untrusted inputs.

## Deliverables checklist
- Code compiles / runs
- Tests added or updated when appropriate
- Notes on edge cases
- Minimal diffs (no drive-by refactors)
"""

# validate.yml for OverKill and AskJamie (no check-accent-contrast step)
VALIDATE_YML_BASE = """\
name: Site Validation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    name: Validate site HTML, links, and structure

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install beautifulsoup4

      - name: Run site validator
        run: python3 scripts/validate-site.py

      - name: Run link checker
        run: python3 scripts/check-links.py

      - name: Rebuild search index
        run: python3 scripts/build-search-index.py
        continue-on-error: false

      - name: Verify search index was built
        run: |
          if [ ! -f assets/data/search-index.json ]; then
            echo "ERROR: search-index.json not found after build step"
            exit 1
          fi
          echo "Search index OK: $(wc -c < assets/data/search-index.json) bytes"
"""

# ---------------------------------------------------------------------------
# Sync manifest
# Each entry: (repo, path_in_repo, local_path_or_None, inline_content_or_None,
#              commit_message)
# If local_path is provided, content is read from disk.
# If inline_content is provided, it is used directly.
# ---------------------------------------------------------------------------

MANIFEST = [
    # AGENTS.md -- per-brand; staged by the operator before running this script
    ("OKHP3/OverKill-Hill",   "AGENTS.md",
     "/tmp/okhp3-sync/okh/AGENTS.md", None,
     "docs(AGENTS): sync canonical v2.0"),
    ("OKHP3/AskJamie",        "AGENTS.md",
     "/tmp/okhp3-sync/askjamie/AGENTS.md", None,
     "docs(AGENTS): sync canonical v2.0"),
    ("OKHP3/Glee-fullyTools", "AGENTS.md",
     "/tmp/okhp3-sync/glee/AGENTS.md", None,
     "docs(AGENTS): sync canonical v2.0"),

    # .editorconfig -- identical across all three repos
    ("OKHP3/OverKill-Hill",   ".editorconfig",
     None, EDITORCONFIG,
     "chore: sync .editorconfig across sibling repos"),
    ("OKHP3/AskJamie",        ".editorconfig",
     None, EDITORCONFIG,
     "chore: sync .editorconfig across sibling repos"),
    ("OKHP3/Glee-fullyTools", ".editorconfig",
     None, EDITORCONFIG,
     "chore: sync .editorconfig across sibling repos"),

    # Copilot instructions -- identical across all three repos
    ("OKHP3/OverKill-Hill",   ".github/copilot-instructions.md",
     None, COPILOT_INSTRUCTIONS,
     "chore: sync Copilot instructions across sibling repos"),
    ("OKHP3/AskJamie",        ".github/copilot-instructions.md",
     None, COPILOT_INSTRUCTIONS,
     "chore: sync Copilot instructions across sibling repos"),
    ("OKHP3/Glee-fullyTools", ".github/copilot-instructions.md",
     None, COPILOT_INSTRUCTIONS,
     "chore: sync Copilot instructions across sibling repos"),

    # validate.yml -- base version for OverKill and AskJamie
    # (Glee's variant adds the check-accent-contrast advisory step)
    ("OKHP3/OverKill-Hill",   ".github/workflows/validate.yml",
     None, VALIDATE_YML_BASE,
     "ci: sync site-validation workflow"),
    ("OKHP3/AskJamie",        ".github/workflows/validate.yml",
     None, VALIDATE_YML_BASE,
     "ci: sync site-validation workflow"),
]


def gh_request(method, path, body=None):
    url = f"{GITHUB_API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "OKHP3-Sync",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        return json.loads(body_text) if body_text else {}, e.code


def get_file_sha(repo, path):
    data, status = gh_request("GET", f"/repos/{repo}/contents/{path}")
    if status == 200:
        return data.get("sha")
    return None


def push_entry(repo, repo_path, local_path, inline_content, commit_message, dry_run=False):
    if inline_content is not None:
        content = inline_content
    elif local_path is not None:
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            return "SKIP", f"local file not found: {local_path}"
    else:
        return "SKIP", "no content source"

    if dry_run:
        return "DRY", f"{len(content)} bytes"

    encoded = base64.b64encode(content.encode()).decode()
    sha = get_file_sha(repo, repo_path)
    body = {"message": commit_message, "content": encoded, "committer": COMMITTER}
    if sha:
        body["sha"] = sha

    data, status = gh_request("PUT", f"/repos/{repo}/contents/{repo_path}", body)
    if status in (200, 201):
        action = "updated" if status == 200 else "created"
        commit_sha = data.get("commit", {}).get("sha", "")[:10]
        return action.upper(), commit_sha
    return "FAIL", data.get("message", f"HTTP {status}")


def main():
    dry_run = "--dry-run" in sys.argv
    token_var = "GITHUB_TOKEN"

    if not TOKEN and not dry_run:
        print(f"ERROR: {token_var} environment variable is not set.")
        print(f"Usage: {token_var}=<pat> python3 scripts/push-to-github.py")
        sys.exit(1)

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"OKHP3 governance sync ({mode}) -- {len(MANIFEST)} entries\n")

    errors = 0
    for repo, repo_path, local_path, inline_content, commit_msg in MANIFEST:
        result, detail = push_entry(
            repo, repo_path, local_path, inline_content, commit_msg, dry_run
        )
        ok = result in ("UPDATED", "CREATED", "DRY")
        tag = "OK" if ok else result
        print(f"  [{tag}] {repo}/{repo_path}  {detail}")
        if not ok and result != "SKIP":
            errors += 1

    print()
    if errors:
        print(f"FAILED: {errors} push(es) did not succeed.")
        sys.exit(1)
    else:
        print("Done.")


if __name__ == "__main__":
    main()
