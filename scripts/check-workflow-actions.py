#!/usr/bin/env python3
"""Validate GitHub Actions references against the repository's version policy.

The approved major versions are documented in docs/ci-action-version-policy.md.
Keep ACTION_MAJOR_VERSIONS and that document in sync when deliberately
upgrading an action. The optional update-review mode checks each action's latest
stable GitHub release without changing the enforcement behavior.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
GITHUB_API_ROOT = "https://api.github.com/repos"
GITHUB_API_TIMEOUT_SECONDS = 20

# Approved major versions for the actions currently used by this repository.
# A missing action is reported as unsupported rather than silently accepted.
ACTION_MAJOR_VERSIONS = {
    "actions/checkout": 4,
    "actions/setup-python": 5,
    "actions/upload-artifact": 4,
    "actions/download-artifact": 4,
    "actions/configure-pages": 5,
    "actions/upload-pages-artifact": 3,
    "actions/deploy-pages": 4,
}

USES_PATTERN = re.compile(
    r"^\s*uses:\s*(?P<action>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@(?P<ref>\S+)"
)
MAJOR_PATTERN = re.compile(r"^v(?P<major>[0-9]+)(?:\b|$)", re.IGNORECASE)


def fetch_latest_release(action: str) -> dict[str, object]:
    """Fetch the latest stable release metadata for an action repository."""
    request = urllib.request.Request(
        f"{GITHUB_API_ROOT}/{action}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "overkill-hill-ci-action-version-review",
        },
    )
    try:
        with urllib.request.urlopen(
            request, timeout=GITHUB_API_TIMEOUT_SECONDS
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"could not fetch latest release: {error}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"GitHub returned invalid release data: {error}") from error

    if not isinstance(payload, dict):
        raise RuntimeError("GitHub returned an unexpected release response")
    return payload


def released_major(
    action: str,
    fetcher: Callable[[str], dict[str, object]] = fetch_latest_release,
) -> int:
    """Return the major number from an action's latest stable release tag."""
    release = fetcher(action)
    tag_name = release.get("tag_name")
    if not isinstance(tag_name, str):
        raise RuntimeError("latest release has no tag_name")

    major_match = MAJOR_PATTERN.match(tag_name)
    if not major_match:
        raise RuntimeError(f"latest release tag {tag_name!r} is not a major tag")
    return int(major_match.group("major"))


def check_for_updates(
    fetcher: Callable[[str], dict[str, object]] = fetch_latest_release,
) -> list[str]:
    """Return errors for unavailable reviews or newer stable action majors."""
    findings: list[str] = []
    for action, approved_major in ACTION_MAJOR_VERSIONS.items():
        try:
            latest_major = released_major(action, fetcher)
        except RuntimeError as error:
            findings.append(f"{action}: update review failed: {error}")
            continue

        if latest_major > approved_major:
            findings.append(
                f"{action}: newer stable major v{latest_major} is available "
                f"(policy currently approves v{approved_major})"
            )
    return findings


def workflow_files(directory: Path = WORKFLOWS_DIR) -> list[Path]:
    """Return workflow YAML files in a stable order."""
    return sorted((*directory.glob("*.yml"), *directory.glob("*.yaml")))


def check_workflows(directory: Path = WORKFLOWS_DIR) -> list[str]:
    """Return human-readable errors for invalid workflow action references."""
    errors: list[str] = []
    files = workflow_files(directory)
    if not files:
        return [f"No workflow files found under {directory}"]

    for workflow in files:
        for line_number, line in enumerate(
            workflow.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = USES_PATTERN.match(line)
            if not match:
                continue

            action = match.group("action")
            ref = match.group("ref")
            expected_major = ACTION_MAJOR_VERSIONS.get(action)
            major_match = MAJOR_PATTERN.match(ref)

            if expected_major is None:
                errors.append(
                    f"{workflow}:{line_number}: unsupported action {action}@{ref}; "
                    "add it to the approved version policy before use"
                )
                continue

            if not major_match:
                errors.append(
                    f"{workflow}:{line_number}: {action}@{ref} must use an approved "
                    f"major tag v{expected_major}"
                )
                continue

            actual_major = int(major_match.group("major"))
            if actual_major != expected_major:
                errors.append(
                    f"{workflow}:{line_number}: {action}@{ref} is not approved; "
                    f"use v{expected_major}"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check GitHub Actions versions used by .github/workflows/"
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=WORKFLOWS_DIR,
        help="workflow directory (used by tests and local checks)",
    )
    parser.add_argument(
        "--check-updates",
        action="store_true",
        help="review each approved action against its latest stable GitHub release",
    )
    args = parser.parse_args()

    errors = check_workflows(args.workflows_dir)
    if errors:
        print("GitHub Actions version policy check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    if args.check_updates:
        update_findings = check_for_updates()
        if update_findings:
            print("GitHub Actions update review needs attention:")
            for finding in update_findings:
                print(f"  - {finding}")
            print(
                "Review the release, then update the policy and workflow "
                "references together if an upgrade is approved."
            )
            return 1
        print("GitHub Actions update review passed (no newer stable majors found).")

    print(
        f"GitHub Actions version policy check passed "
        f"({len(workflow_files(args.workflows_dir))} workflow files)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())