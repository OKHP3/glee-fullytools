#!/usr/bin/env python3
"""Fail when a Pages artifact contains internal or development-only files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from public_inventory import expected_public_top_level, forbidden_artifact_parts

PUBLIC_DOCUMENTATION_PATHS = {
    "docs",
    "docs/organization-identity-approval.json",
}


def check_artifact(root: Path) -> list[str]:
    issues: list[str] = []
    allowed_top = expected_public_top_level()
    forbidden = forbidden_artifact_parts()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        relative = rel.as_posix()
        if rel.parts and rel.parts[0] not in allowed_top:
            issues.append(f"top-level path is not public: {relative}")
        if relative not in PUBLIC_DOCUMENTATION_PATHS and any(
            part in forbidden for part in rel.parts
        ):
            issues.append(f"forbidden artifact path: {relative}")
    assets = root / "assets"
    if assets.is_dir():
        allowed_assets = {"css", "data", "img", "js", "vendor"}
        for child in assets.iterdir():
            if child.name not in allowed_assets:
                issues.append(f"assets path is not in the public allowlist: {child.relative_to(root).as_posix()}")
    provenance = root / "release-provenance.json"
    if not provenance.is_file():
        issues.append("release-provenance.json is missing")
    approval_record = root / "docs" / "organization-identity-approval.json"
    if not approval_record.is_file():
        issues.append(
            "required public file missing: docs/organization-identity-approval.json"
        )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Pages artifact directory to inspect")
    args = parser.parse_args()
    issues = check_artifact(args.root)
    if issues:
        print("Pages artifact policy failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(f"Pages artifact policy passed: {args.root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())