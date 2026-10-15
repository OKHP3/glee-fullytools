#!/usr/bin/env python3
"""Verify GitHub's effective retention period for the Pages evidence artifact."""

from datetime import datetime, timedelta, timezone
import argparse
import hashlib
from http.client import IncompleteRead
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, urlopen
import zipfile
import zlib


REQUIRED_RETENTION = timedelta(days=90)
API_VERSION = "2022-11-28"
DOWNLOAD_CHUNK_SIZE = 64 * 1024
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 10_000
MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
REQUIRED_EVIDENCE_FILES = {
    "assets/audit/color-scheme-init-chromium.json",
    "assets/audit/color-scheme-init-firefox.json",
    "assets/audit/color-scheme-init-webkit.json",
    "assets/audit/color-scheme-evidence-index.md",
    "assets/docs/audit-report.md",
}
# The source revision that first requested 90-day Pages evidence retention.
# Earlier successful releases did not promise this artifact lifetime.
RETENTION_POLICY_COMMIT = "edf2d3509e6b51cdd42ad36cd9ca1dd111cfd08e"


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
    artifact: dict[str, object], expected_id: int, expected_name: str,
    workflow_run: dict[str, object], expected_run_id: int, expected_commit: str,
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

    associated_run = artifact.get("workflow_run")
    if not isinstance(associated_run, dict):
        raise ValueError("GitHub artifact metadata is missing workflow_run")
    for source, metadata in (("artifact", associated_run), ("workflow", workflow_run)):
        if metadata.get("id") != expected_run_id:
            raise ValueError(f"GitHub {source} run id does not match {expected_run_id}")
        if metadata.get("head_sha") != expected_commit:
            raise ValueError(f"GitHub {source} run commit does not match {expected_commit}")

    # GitHub caps artifact expiry at the associated original run's retention
    # deadline. Uploads and rerun attempts do not restart that clock.
    run_created_at = parse_timestamp(workflow_run.get("created_at"), "workflow run created_at")
    created_at = parse_timestamp(artifact.get("created_at"), "created_at")
    expires_at = parse_timestamp(artifact.get("expires_at"), "expires_at")
    if created_at < run_created_at:
        raise ValueError("GitHub reports an artifact created before its workflow run")
    if created_at >= expires_at:
        raise ValueError("GitHub artifact must be created before its expiration")
    actual_retention = expires_at - run_created_at
    if actual_retention < REQUIRED_RETENTION:
        raise ValueError(
            "GitHub reports an artifact retention period of "
            f"{actual_retention}, shorter than the approved 90 days"
        )


def api_page(url: str, token: str) -> tuple[dict[str, object], str | None]:
    """Fetch one GitHub API page and return its next-page URL, if any."""
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "Glee-fully-Pages-evidence-retention-check",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("GitHub API response must be a JSON object")
        link_header = response.headers.get("Link", "")

    next_match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
    next_url = urljoin(url, next_match.group(1)) if next_match else None
    return payload, next_url


def verify_artifact_download(
    repository: str,
    artifact_id: int,
    api_url: str,
    token: str,
    *,
    expected_digest: str | None = None,
    open_url=None,
) -> None:
    """Stream and validate an evidence ZIP using bounded temporary storage."""
    url = (
        f"{api_url.rstrip('/')}/repos/{repository}/actions/artifacts/"
        f"{artifact_id}/zip"
    )
    digest_match = None
    if expected_digest is not None:
        digest_match = re.fullmatch(r"sha256:([0-9a-fA-F]{64})", expected_digest)
        if not digest_match:
            raise ValueError(
                f"GitHub artifact metadata has an invalid digest: {expected_digest!r}"
            )
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "Glee-fully-Pages-evidence-retention-check",
        },
    )
    # GitHub redirects to signed artifact storage; authorize only the API request.
    request.add_unredirected_header("Authorization", f"Bearer {token}")
    open_request = open_url or urlopen
    try:
        with open_request(request, timeout=30) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise ValueError(
                    f"artifact download endpoint returned HTTP {status}"
                )
            headers = getattr(response, "headers", {})
            content_length = headers.get("Content-Length")
            try:
                expected_length = (
                    int(content_length) if content_length is not None else None
                )
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "artifact download has an invalid Content-Length"
                ) from error
            if expected_length is not None and expected_length < 0:
                raise ValueError("artifact download has a negative Content-Length")

            downloaded = 0
            digest = hashlib.sha256()
            with tempfile.TemporaryFile(mode="w+b") as archive:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > MAX_ARTIFACT_BYTES:
                        raise ValueError(
                            "artifact download exceeds the 512 MiB size limit"
                        )
                    archive.write(chunk)
                    digest.update(chunk)
                if expected_length is not None and downloaded != expected_length:
                    raise ValueError(
                        "artifact download is incomplete "
                        f"({downloaded} of {expected_length} bytes)"
                    )
                if (
                    digest_match
                    and digest.hexdigest().lower()
                    != digest_match.group(1).lower()
                ):
                    raise ValueError(
                        "artifact download does not match GitHub's SHA-256 digest"
                    )
                validate_artifact_archive(archive)
    except (
        OSError,
        TimeoutError,
        ValueError,
        zipfile.BadZipFile,
        EOFError,
        IncompleteRead,
        zlib.error,
    ) as error:
        raise ValueError(f"artifact download failed: {error}") from error


def validate_artifact_archive(archive) -> None:
    """Check ZIP structure, CRCs, and the required review reports."""
    try:
        archive.seek(0)
        with zipfile.ZipFile(archive) as zipped:
            entries = zipped.infolist()
            if len(entries) > MAX_ARCHIVE_ENTRIES:
                raise ValueError(
                    f"artifact archive has more than {MAX_ARCHIVE_ENTRIES} entries"
                )
            expanded_size = sum(entry.file_size for entry in entries)
            if expanded_size > MAX_UNCOMPRESSED_BYTES:
                raise ValueError(
                    "artifact archive expands beyond the 512 MiB size limit"
                )
            names = {entry.filename for entry in entries}
            missing = sorted(REQUIRED_EVIDENCE_FILES - names)
            if missing:
                raise ValueError(
                    "artifact archive is missing required evidence files: "
                    + ", ".join(missing)
                )
            damaged = zipped.testzip()
            if damaged is not None:
                raise ValueError(f"artifact archive has a damaged file: {damaged}")
    except (
        zipfile.BadZipFile,
        EOFError,
        RuntimeError,
        OSError,
        zlib.error,
        NotImplementedError,
    ) as error:
        raise ValueError(f"artifact archive is corrupt or incomplete: {error}") from error


def _list_all(
    url: str,
    collection_key: str,
    token: str,
    fetch_page=None,
) -> list[dict[str, object]]:
    fetch = fetch_page or api_page
    items: list[dict[str, object]] = []
    while url:
        payload, next_url = fetch(url, token)
        page_items = payload.get(collection_key)
        if not isinstance(page_items, list):
            raise ValueError(
                f"GitHub API response is missing the {collection_key} list"
            )
        if any(not isinstance(item, dict) for item in page_items):
            raise ValueError(
                f"GitHub API {collection_key} entries must be JSON objects"
            )
        items.extend(page_items)
        url = next_url
    return items


def monitor_repository(
    repository: str,
    api_url: str,
    token: str,
    *,
    now: datetime | None = None,
    fetch_page=None,
    open_url=None,
) -> int:
    """Fail if a successful Pages run loses its evidence inside the 90-day window."""
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise ValueError("monitor time must include a timezone")
    cutoff = current_time - REQUIRED_RETENTION
    workflow_path = quote("pages.yml", safe="")
    query = urlencode(
        {
            "status": "completed",
            "created": f">={cutoff.date().isoformat()}",
            "per_page": 100,
        }
    )
    runs_url = (
        f"{api_url.rstrip('/')}/repos/{repository}/actions/workflows/"
        f"{workflow_path}/runs?{query}"
    )
    runs = _list_all(runs_url, "workflow_runs", token, fetch_page)
    checked = 0
    failures: list[str] = []

    for run in runs:
        if run.get("conclusion") != "success":
            continue
        run_id = run.get("id")
        commit = run.get("head_sha")
        try:
            run_created_at = parse_timestamp(
                run.get("created_at"), "workflow run created_at"
            )
        except ValueError as error:
            failures.append(
                f"run {run_id if isinstance(run_id, int) else 'unknown'} | "
                f"commit {commit if isinstance(commit, str) and commit else 'unknown'} | "
                f"review deadline unknown: {error}"
            )
            continue
        deadline = run_created_at + REQUIRED_RETENTION
        if deadline <= current_time:
            continue
        if not isinstance(run_id, int) or not isinstance(commit, str) or not commit:
            failures.append(
                f"run {run_id if isinstance(run_id, int) else 'unknown'} | "
                f"commit {commit if isinstance(commit, str) and commit else 'unknown'} | "
                f"review deadline {deadline.isoformat()}: "
                "successful Pages run is missing a numeric id or commit SHA"
            )
            continue

        try:
            compare_url = (
                f"{api_url.rstrip('/')}/repos/{repository}/compare/"
                f"{RETENTION_POLICY_COMMIT}...{quote(commit, safe='')}"
            )
            comparison, _ = (fetch_page or api_page)(compare_url, token)
            policy_status = (
                comparison.get("status") if isinstance(comparison, dict) else None
            )
            if policy_status == "behind":
                continue
            if policy_status not in ("ahead", "identical"):
                raise ValueError(
                    "cannot establish retention-policy ancestry "
                    f"(comparison status {policy_status!r})"
                )

            artifacts_url = (
                f"{api_url.rstrip('/')}/repos/{repository}/actions/runs/{run_id}"
                f"/artifacts?include_expired=true&per_page=100"
            )
            artifacts = _list_all(
                artifacts_url, "artifacts", token, fetch_page
            )
            expected_name = f"pages-validation-{commit}"
            matching = [
                item for item in artifacts if item.get("name") == expected_name
            ]
            if not matching:
                raise ValueError("validation artifact is missing")

            errors = []
            for artifact in matching:
                try:
                    artifact_id = artifact.get("id")
                    if not isinstance(artifact_id, int):
                        raise ValueError(
                            "GitHub artifact metadata is missing a numeric id"
                        )
                    validate_artifact(
                        artifact,
                        artifact_id,
                        expected_name,
                        run,
                        run_id,
                        commit,
                    )
                    expires_at = parse_timestamp(
                        artifact.get("expires_at"), "expires_at"
                    )
                    if expires_at <= current_time:
                        raise ValueError("GitHub reports that the artifact expired early")
                    verify_artifact_download(
                        repository,
                        artifact_id,
                        api_url,
                        token,
                        expected_digest=(
                            artifact.get("digest")
                            if isinstance(artifact.get("digest"), str)
                            else None
                        ),
                        open_url=open_url,
                    )
                except (OSError, TimeoutError, ValueError) as error:
                    errors.append(str(error))
                else:
                    break
            else:
                raise ValueError(
                    f"validation artifact is invalid or unavailable: {'; '.join(errors)}"
                )
        except (OSError, TimeoutError, ValueError) as error:
            failures.append(
                f"run {run_id} | commit {commit} | "
                f"review deadline {deadline.isoformat()}: {error}"
            )
            continue
        checked += 1

    if failures:
        raise ValueError(
            "Pages validation retention check found problems in active review "
            f"windows ({len(failures)}):\n- " + "\n- ".join(failures)
        )
    return checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monitor-window", action="store_true")
    parser.add_argument("--repository")
    parser.add_argument("--api-url")
    parser.add_argument("--token", default=None)
    parser.add_argument("--artifact-id", type=int)
    parser.add_argument("--artifact-name")
    parser.add_argument("--run-metadata", type=Path)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--commit")
    args = parser.parse_args()

    try:
        if args.monitor_window:
            if not args.repository or not args.api_url or not args.token:
                raise ValueError(
                    "window monitoring requires --repository, --api-url, "
                    "and --token"
                )
            checked = monitor_repository(
                args.repository, args.api_url, args.token
            )
            print(
                f"Verified {checked} Pages validation artifact(s) within the "
                "active 90-day review window."
            )
            return 0

        if (
            args.artifact_id is None
            or not args.artifact_name
            or args.run_metadata is None
            or args.run_id is None
            or not args.commit
        ):
            raise ValueError(
                "artifact verification requires --artifact-id, --artifact-name, "
                "--run-metadata, --run-id, and --commit"
            )
        artifact = json.load(sys.stdin)
        if not isinstance(artifact, dict):
            raise ValueError("GitHub artifact response must be a JSON object")
        workflow_run = json.loads(args.run_metadata.read_text(encoding="utf-8"))
        if not isinstance(workflow_run, dict):
            raise ValueError("GitHub workflow run response must be a JSON object")
        validate_artifact(
            artifact, args.artifact_id, args.artifact_name,
            workflow_run, args.run_id, args.commit,
        )
    except (json.JSONDecodeError, OSError, ValueError) as error:
        print(
            f"Pages validation artifact retention check failed: {error}",
            file=sys.stderr,
        )
        return 1

    print("Verified the Pages validation artifact is retained for at least 90 days "
          "from original workflow run creation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
