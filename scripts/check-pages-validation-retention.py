#!/usr/bin/env python3
"""Verify GitHub's effective retention period for the Pages evidence artifact."""

from datetime import datetime, timedelta
import argparse
import json
import sys


REQUIRED_RETENTION = timedelta(days=90)


def parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"artifact metadata is missing {field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"artifact metadata has invalid {field}: {value!r}") from error
    if parsed.tzinfo is None:
        raise ValueError(f"artifact metadata {field} must include a timezone")
    return parsed


def validate_artifact(
    artifact: dict[str, object], expected_id: int, expected_name: str
) -> None:
    if artifact.get("id") != expected_id:
        raise ValueError(
            f"GitHub returned artifact id {artifact.get('id')!r}, "
            f"expected {expected_id}"
        )
    if artifact.get("name") != expected_name:
        raise ValueError(
            f"GitHub returned artifact name {artifact.get('name')!r}, "
            f"expected {expected_name!r}"
        )
    if artifact.get("expired") is not False:
        raise ValueError("GitHub reports that the validation artifact is expired")

    created_at = parse_timestamp(artifact.get("created_at"), "created_at")
    expires_at = parse_timestamp(artifact.get("expires_at"), "expires_at")
    actual_retention = expires_at - created_at
    if actual_retention < REQUIRED_RETENTION:
        raise ValueError(
            "GitHub reports an artifact retention period of "
            f"{actual_retention}, shorter than the approved 90 days"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--artifact-name", required=True)
    args = parser.parse_args()

    try:
        artifact = json.load(sys.stdin)
        if not isinstance(artifact, dict):
            raise ValueError("GitHub artifact response must be a JSON object")
        validate_artifact(artifact, args.artifact_id, args.artifact_name)
    except (json.JSONDecodeError, OSError, ValueError) as error:
        print(
            f"Pages validation artifact retention check failed: {error}",
            file=sys.stderr,
        )
        return 1

    print("Verified the Pages validation artifact is retained for at least 90 days.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())