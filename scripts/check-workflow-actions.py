#!/usr/bin/env python3
"""Validate GitHub Actions references against the repository's version policy.

The approved major versions are documented in docs/ci-action-version-policy.md.
Keep ACTION_MAJOR_VERSIONS and that document in sync when deliberately
upgrading an action.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = ROOT / ".github" / "workflows"

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
    args = parser.parse_args()

    errors = check_workflows(args.workflows_dir)
    if errors:
        print("GitHub Actions version policy check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"GitHub Actions version policy check passed "
        f"({len(workflow_files(args.workflows_dir))} workflow files)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())