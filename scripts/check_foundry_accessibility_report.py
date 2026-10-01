#!/usr/bin/env python3
"""Validate the focused FoundRy accessibility report contract."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit


EXPECTED_VIEWPORTS = [
    {"name": "narrow-320", "width": 320, "height": 780},
    {"name": "narrow-390", "width": 390, "height": 844},
]
STATUSES = ("PASS", "FAIL", "NOT RUN")
SCREEN_READER_LIMITATION = "Human screen-reader testing was not run."
SOURCE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _is_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


def validate_report(report: object) -> list[str]:
    """Return every report-contract violation without changing the report."""
    if not isinstance(report, dict):
        return ["report must be a JSON object"]

    errors: list[str] = []
    if not _is_utc_timestamp(report.get("generatedAt")):
        errors.append("generatedAt must be a UTC ISO-8601 timestamp ending in Z")

    source_sha = report.get("sourceSha")
    if not isinstance(source_sha, str) or not SOURCE_SHA_PATTERN.fullmatch(source_sha):
        errors.append("sourceSha must be a 40-character lowercase Git SHA")

    if report.get("route") != "/foundry/":
        errors.append("route must be /foundry/")

    if report.get("viewports") != EXPECTED_VIEWPORTS:
        errors.append(
            "viewports must contain narrow-320 at 320x780 and narrow-390 at 390x844"
        )

    runtime = report.get("runtime")
    runtime_status = None
    if not isinstance(runtime, dict):
        errors.append("runtime must be an object")
    else:
        runtime_status = runtime.get("status")
        if runtime_status == "RUN":
            driver = runtime.get("driver")
            if not isinstance(driver, str) or not driver.strip():
                errors.append("runtime RUN status requires a driver")
            base_url = report.get("baseUrl")
            try:
                parsed_url = urlsplit(base_url) if isinstance(base_url, str) else None
                port = parsed_url.port if parsed_url else None
            except ValueError:
                parsed_url = None
                port = None
            if (
                parsed_url is None
                or parsed_url.scheme != "http"
                or parsed_url.hostname != "127.0.0.1"
                or port is None
                or parsed_url.path not in ("", "/")
                or parsed_url.query
                or parsed_url.fragment
            ):
                errors.append("runtime RUN status requires the loopback baseUrl")
        elif runtime_status == "NOT RUN":
            reason = runtime.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append("runtime NOT RUN status requires a reason")
        else:
            errors.append("runtime status must be RUN or NOT RUN")

    checks_value = report.get("checks")
    checks = checks_value if isinstance(checks_value, list) else []
    if not isinstance(checks_value, list):
        errors.append("checks must be a list")

    status_counts = {status: 0 for status in STATUSES}
    seen_names: set[str] = set()
    checked_viewports: set[str] = set()
    expected_viewport_names = {viewport["name"] for viewport in EXPECTED_VIEWPORTS}

    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"checks[{index}] must be an object")
            continue

        name = check.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"checks[{index}] must have a non-empty name")
        elif name in seen_names:
            errors.append(f"check name is duplicated: {name}")
        else:
            seen_names.add(name)
            viewport, separator, _ = name.partition(": ")
            if not separator or viewport not in expected_viewport_names:
                errors.append(f"check name has no recognized narrow viewport: {name}")
            else:
                checked_viewports.add(viewport)

        status = check.get("status")
        if status not in STATUSES:
            errors.append(f"checks[{index}] status must be PASS, FAIL, or NOT RUN")
            continue
        status_counts[status] += 1

        if status == "FAIL":
            error = check.get("error")
            if not isinstance(error, str) or not error.strip():
                errors.append(f"failed check {name!r} must include an error")
        elif status == "PASS" and "error" in check:
            errors.append(f"passing check {name!r} must not include an error")

    if runtime_status == "RUN":
        missing_viewports = sorted(expected_viewport_names - checked_viewports)
        if missing_viewports:
            errors.append(
                "runtime RUN report has no checks for: " + ", ".join(missing_viewports)
            )
    elif runtime_status == "NOT RUN" and checks:
        errors.append("runtime NOT RUN report must not contain browser checks")

    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
    else:
        extra_statuses = set(summary) - set(STATUSES)
        if extra_statuses:
            errors.append("summary contains unsupported status counts")
        for status in STATUSES:
            count = summary.get(status)
            if type(count) is not int or count < 0:
                errors.append(f"summary {status} count must be a non-negative integer")
            elif count != status_counts[status]:
                errors.append(
                    f"summary {status} count is {count}, but checks contain "
                    f"{status_counts[status]}"
                )

    limitations = report.get("limitations")
    if (
        not isinstance(limitations, list)
        or SCREEN_READER_LIMITATION not in limitations
    ):
        errors.append(
            "limitations must state that human screen-reader testing was not run"
        )

    return errors


def validate_file(path: Path) -> list[str]:
    """Load and validate one JSON report, returning readable errors."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        return [f"could not read report: {error}"]
    except UnicodeDecodeError as error:
        return [f"report is not valid UTF-8: {error}"]
    except json.JSONDecodeError as error:
        return [f"report is invalid JSON: {error}"]
    return validate_report(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="FoundRy accessibility report JSON")
    args = parser.parse_args(argv)

    errors = validate_file(args.report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"FoundRy accessibility report contract is valid: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())