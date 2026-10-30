#!/usr/bin/env python3
"""Verify GitHub's effective retention period for the Pages evidence artifact."""

from datetime import datetime, timedelta, timezone
import argparse
from email.utils import parsedate_to_datetime
import hashlib
from http.client import IncompleteRead
import json
from pathlib import Path
import re
import math
import stat
import sys
import tempfile
from urllib.error import HTTPError, URLError
import time
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen
import zipfile
import zlib


REQUIRED_RETENTION = timedelta(days=90)
API_VERSION = "2022-11-28"
DOWNLOAD_CHUNK_SIZE = 64 * 1024
DOWNLOAD_MAX_ATTEMPTS = 3
DOWNLOAD_MAX_RETRY_WAIT_SECONDS = 60
DOWNLOAD_RETRY_BACKOFF_SECONDS = 1
METADATA_MAX_ATTEMPTS = 3
METADATA_RETRY_BACKOFF_SECONDS = 1
METADATA_MAX_RETRY_WAIT_SECONDS = 60
# The scheduled workflow has a 10-minute hard timeout. Keep the monitor's
# shared wall-clock budget to 7 minutes so checkout, startup, and reporting
# retain at least 3 minutes of margin. Every API/download attempt and retry wait
# uses this same budget across all active runs.
MONITOR_RUNTIME_BUDGET_SECONDS = 7 * 60
REQUEST_TIMEOUT_SECONDS = 30
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


class _RetryBudgetExceeded(TimeoutError):
    def __init__(self, seconds: float):
        self.seconds = seconds
        super().__init__(
            f"shared monitor time budget exhausted after {seconds:g} seconds"
        )


class _RuntimeBudget:
    """Shared wall-clock allowance for all monitor requests and retry waits."""

    def __init__(self, seconds: float, *, clock=None, sleeper=None):
        self.seconds = seconds
        self._clock = clock or time.monotonic
        self._sleep = sleeper or time.sleep
        self.deadline = self._clock() + seconds

    def remaining(self) -> float:
        return max(0.0, self.deadline - self._clock())

    def request_timeout(self) -> float:
        remaining = self.remaining()
        if remaining <= 0:
            raise _RetryBudgetExceeded(self.seconds)
        return min(REQUEST_TIMEOUT_SECONDS, remaining)

    def ensure_available(self) -> None:
        if self.remaining() <= 0:
            raise _RetryBudgetExceeded(self.seconds)

    def wait(self, seconds: float) -> None:
        remaining = self.remaining()
        if remaining <= 0:
            raise _RetryBudgetExceeded(self.seconds)
        self._sleep(min(seconds, remaining))
        self.ensure_available()


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


def api_page(
    url: str, token: str, *, timeout: float = REQUEST_TIMEOUT_SECONDS
) -> tuple[dict[str, object], str | None]:
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
    with urlopen(request, timeout=timeout) as response:
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
    budget: _RuntimeBudget | None = None,
) -> int:
    """Stream and validate an evidence ZIP using bounded temporary storage."""
    open_request = open_url or urlopen
    retry_wait = 0
    for attempt in range(1, DOWNLOAD_MAX_ATTEMPTS + 1):
        try:
            if budget is not None:
                budget.ensure_available()
            _verify_artifact_download_once(
                repository,
                artifact_id,
                api_url,
                token,
                expected_digest=expected_digest,
                open_request=open_request,
                budget=budget,
            )
            if budget is not None:
                budget.ensure_available()
            return attempt - 1
        except _RetryBudgetExceeded:
            raise
        except _RetryableDownloadError as error:
            if attempt == DOWNLOAD_MAX_ATTEMPTS:
                raise ValueError(
                    f"artifact download failed after {attempt} attempts: {error}"
                ) from error
            delay = DOWNLOAD_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            if budget is None:
                time.sleep(delay)
            else:
                budget.wait(delay)
            retry_wait += delay
        except HTTPError as error:
            try:
                delay = _http_download_retry_delay(error, attempt)
            finally:
                # Release the response before sleeping, retrying, or failing.
                error.close()
            if delay is None:
                raise ValueError(f"artifact download failed: {error}") from error
            if attempt == DOWNLOAD_MAX_ATTEMPTS:
                raise ValueError(
                    f"artifact download failed after {attempt} attempts: {error}"
                ) from error
            if delay > DOWNLOAD_MAX_RETRY_WAIT_SECONDS - retry_wait:
                raise ValueError(
                    "artifact download rate-limited; retry deferred because the "
                    "server's requested wait exceeds the remaining 60-second retry budget"
                ) from error
            if budget is None:
                time.sleep(delay)
            else:
                budget.wait(delay)
            retry_wait += delay
        except (
            ValueError,
            zipfile.BadZipFile,
            EOFError,
            IncompleteRead,
            OSError,
            TimeoutError,
            URLError,
            zlib.error,
        ) as error:
            raise ValueError(f"artifact download failed: {error}") from error


class _RetryableDownloadError(Exception):
    """A transfer may succeed if the complete request is attempted again."""


def _is_retryable_http_status(status: int) -> bool:
    return status in (408, 429) or 500 <= status <= 599


def _fetch_metadata_page(
    url: str,
    token: str,
    fetch_page=None,
    budget: _RuntimeBudget | None = None,
) -> tuple[dict[str, object], str | None]:
    """Fetch a metadata page, retrying temporary API and transport failures."""
    fetch = fetch_page or api_page
    retry_wait = 0
    for attempt in range(1, METADATA_MAX_ATTEMPTS + 1):
        delay = METADATA_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
        try:
            if budget is None:
                return fetch(url, token)
            budget.ensure_available()
            if fetch_page is None:
                result = api_page(url, token, timeout=budget.request_timeout())
            else:
                result = fetch(url, token)
            budget.ensure_available()
            return result
        except _RetryBudgetExceeded:
            raise
        except HTTPError as error:
            try:
                delay = _http_download_retry_delay(error, attempt, label="GitHub metadata request")
            finally:
                error.close()
            if delay is None:
                raise ValueError(
                    f"GitHub metadata request failed with HTTP {error.code}: {error}"
                ) from error
            if attempt == METADATA_MAX_ATTEMPTS:
                raise ValueError(
                    f"GitHub metadata request failed after {attempt} attempts "
                    f"(HTTP {error.code}): {error}"
                ) from error
            if delay > METADATA_MAX_RETRY_WAIT_SECONDS - retry_wait:
                raise ValueError(
                    "GitHub metadata retry deferred: server wait exceeds the "
                    "remaining 60-second retry budget"
                ) from error
        except (URLError, TimeoutError, OSError) as error:
            if attempt == METADATA_MAX_ATTEMPTS:
                raise ValueError(
                    f"GitHub metadata request failed after {attempt} attempts: {error}"
                ) from error
        if budget is None:
            time.sleep(delay)
        else:
            budget.wait(delay)
        retry_wait += delay
    raise AssertionError("metadata retry loop exited unexpectedly")


def _http_download_retry_delay(
    error: HTTPError, attempt: int, *, label: str = "artifact download"
) -> float | None:
    """Honor GitHub throttles without retrying ordinary authorization failures.

    https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api#rate-limit-errors
    """
    headers = {key.lower(): value for key, value in (error.headers or {}).items()}
    throttled = error.code == 429 or (
        error.code == 403
        and ("retry-after" in headers or headers.get("x-ratelimit-remaining") == "0")
    )
    if error.code == 403 and not throttled:
        # Secondary throttles may identify themselves only in the error message.
        try:
            message = error.read(4096).lower()
        except (OSError, IncompleteRead):
            message = b""
        throttled = b"rate limit" in message or b"rate-limit" in message
    if not throttled and not _is_retryable_http_status(error.code):
        return None
    if "retry-after" in headers:
        try:
            retry_after = headers["retry-after"]
            try:
                delay = float(retry_after)
            except ValueError:
                now = datetime.fromtimestamp(time.time(), timezone.utc)
                retry_at = _parse_http_date(retry_after.strip(), now)
                delay = max(0.0, (retry_at - now).total_seconds())
            if not math.isfinite(delay) or delay < 0:
                raise ValueError("invalid retry interval")
            return delay
        except (TypeError, ValueError, OverflowError, OSError) as invalid:
            raise ValueError(f"{label} retry deferred: invalid Retry-After") from invalid
    if throttled:
        if headers.get("x-ratelimit-remaining") == "0":
            try:
                reset = float(headers["x-ratelimit-reset"])
                if not math.isfinite(reset):
                    raise ValueError("invalid reset time")
                return max(0, math.ceil(reset - time.time()) + 1)
            except (KeyError, TypeError, ValueError) as invalid:
                raise ValueError(f"{label} retry deferred: invalid rate-limit reset") from invalid
        return 60 * (2 ** (attempt - 1))
    return DOWNLOAD_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))


def _parse_http_date(value: str, now: datetime) -> datetime:
    """Parse the three HTTP-date forms with the RFC 850 rolling year rule."""
    weekday = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
    long_weekday = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
    month = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    clock = r"[0-9]{2}:[0-9]{2}:[0-9]{2}"
    flags = re.IGNORECASE | re.ASCII

    if re.fullmatch(
        rf"{weekday}, [0-9]{{2}} {month} [0-9]{{4}} {clock} GMT", value, flags
    ):
        return parsedate_to_datetime(value)

    obsolete = re.fullmatch(
        rf"{long_weekday}, (?P<day>[0-9]{{2}})-(?P<month>{month})-"
        rf"(?P<year>[0-9]{{2}}) (?P<clock>{clock}) GMT",
        value,
        flags,
    )
    if obsolete:
        # Parse against a leap year first, then choose the century relative to
        # the current date instead of email.utils' fixed two-digit-year pivot.
        parts = parsedate_to_datetime(
            f"{obsolete['day']} {obsolete['month']} 2000 {obsolete['clock']} GMT"
        )
        year = now.year - now.year % 100 + int(obsolete["year"])
        candidate = (year, parts.month, parts.day, parts.hour, parts.minute, parts.second, 0)
        current = (now.month, now.day, now.hour, now.minute, now.second, now.microsecond)
        if candidate > (now.year + 50, *current):
            year -= 100
        elif candidate <= (now.year - 50, *current):
            year += 100
        return parts.replace(year=year)

    if re.fullmatch(
        rf"{weekday} {month} (?:[0-9]{{2}}| [0-9]) {clock} [0-9]{{4}}",
        value,
        flags,
    ):
        return parsedate_to_datetime(value).replace(tzinfo=timezone.utc)

    raise ValueError("invalid HTTP-date")


def _verify_artifact_download_once(
    repository: str,
    artifact_id: int,
    api_url: str,
    token: str,
    *,
    expected_digest: str | None,
    open_request,
    budget: _RuntimeBudget | None = None,
) -> None:
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
    try:
        try:
            timeout = (
                budget.request_timeout()
                if budget is not None
                else REQUEST_TIMEOUT_SECONDS
            )
            response_context = open_request(request, timeout=timeout)
        except HTTPError:
            raise
        except _RetryBudgetExceeded:
            raise
        except (OSError, TimeoutError, URLError) as error:
            raise _RetryableDownloadError(
                f"temporary transport error: {error}"
            ) from error
        with response_context as response:
            status = getattr(response, "status", 200)
            if status != 200:
                if _is_retryable_http_status(status) or status == 403:
                    raise HTTPError(url, status, "Artifact download HTTP error",
                                    getattr(response, "headers", {}), None)
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
                    if budget is not None:
                        budget.ensure_available()
                    try:
                        chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                    except (
                        OSError,
                        TimeoutError,
                        URLError,
                        IncompleteRead,
                        EOFError,
                    ) as error:
                        raise _RetryableDownloadError(
                            f"temporary interruption while reading artifact: {error}"
                        ) from error
                    if budget is not None:
                        budget.ensure_available()
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
                    raise _RetryableDownloadError(
                        "artifact download was interrupted "
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
    except _RetryableDownloadError:
        raise
    except HTTPError:
        raise
    except (
        OSError,
        TimeoutError,
        ValueError,
        zipfile.BadZipFile,
        EOFError,
        IncompleteRead,
        URLError,
        zlib.error,
    ):
        raise


def _required_local_encryption_flags(archive, entry, archive_size: int) -> int:
    """Read encryption flags from a bounded local header using ZIP-adjusted offsets."""
    offset = entry.header_offset
    if offset < 0 or offset > archive_size - 30:
        raise ValueError(f"required evidence entry has an invalid local header: {entry.filename}")
    archive.seek(offset)
    header = archive.read(30)
    if len(header) != 30 or header[:4] != b"PK\x03\x04":
        raise ValueError(f"required evidence entry has an invalid local header: {entry.filename}")
    name_length = int.from_bytes(header[26:28], "little")
    extra_length = int.from_bytes(header[28:30], "little")
    if offset + 30 + name_length + extra_length > archive_size:
        raise ValueError(f"required evidence entry has a truncated local header: {entry.filename}")
    return int.from_bytes(header[6:8], "little") & 0x41


def validate_artifact_archive(archive) -> None:
    """Check ZIP structure, CRCs, and the required review reports."""
    try:
        archive.seek(0)
        with zipfile.ZipFile(archive) as zipped:
            entries = zipped.infolist()
            archive.seek(0, 2)
            archive_size = archive.tell()
            if len(entries) > MAX_ARCHIVE_ENTRIES:
                raise ValueError(
                    f"artifact archive has more than {MAX_ARCHIVE_ENTRIES} entries"
                )
            expanded_size = sum(entry.file_size for entry in entries)
            if expanded_size > MAX_UNCOMPRESSED_BYTES:
                raise ValueError(
                    "artifact archive expands beyond the 512 MiB size limit"
                )
            path_counts: dict[str, int] = {}
            effective_counts: dict[str, int] = {}
            for entry in entries:
                # Also check zipfile's effective names, since testzip opens by
                # that name and may otherwise read one colliding entry twice.
                name = entry.orig_filename
                path_counts[name] = path_counts.get(name, 0) + 1
                name = entry.filename
                effective_counts[name] = effective_counts.get(name, 0) + 1
                if entry.filename in REQUIRED_EVIDENCE_FILES:
                    # POSIX mode bits are meaningful for Unix-created ZIPs.
                    # DOS or type-unspecified metadata cannot prove a member
                    # is regular, but remains compatible with older artifacts.
                    mode = entry.external_attr >> 16 if entry.create_system == 3 else 0
                    file_type = stat.S_IFMT(mode)
                    if (
                        entry.is_dir()
                        or entry.external_attr & 0x10
                        or file_type not in (0, stat.S_IFREG)
                    ):
                        raise ValueError(
                            "required evidence entry is not a regular file: "
                            f"{entry.filename}"
                        )
                    local_flags = _required_local_encryption_flags(archive, entry, archive_size)
                    if (entry.flag_bits & 0x41) or local_flags:
                        raise ValueError(
                            "artifact archive contains an encrypted required "
                            f"evidence file: {entry.filename}"
                        )
            duplicates = ({name for name, count in path_counts.items() if count > 1}
                          | {name for name, count in effective_counts.items() if count > 1})
            required_duplicates = sorted(duplicates & REQUIRED_EVIDENCE_FILES)
            if duplicates:
                if required_duplicates:
                    detail = ", ".join(required_duplicates)
                    if duplicates - REQUIRED_EVIDENCE_FILES:
                        detail += "; additional duplicate paths omitted"
                    raise ValueError("artifact archive has duplicate paths: " + detail)
                raise ValueError("artifact archive has duplicate paths outside required evidence")
            names = {entry.filename for entry in entries}
            missing = sorted(REQUIRED_EVIDENCE_FILES - names)
            if missing:
                raise ValueError(
                    "artifact archive is missing required evidence files: "
                    + ", ".join(missing)
                )
            damaged = zipped.testzip()
            if damaged is not None:
                if damaged in REQUIRED_EVIDENCE_FILES:
                    raise ValueError(f"artifact archive has a damaged file: {damaged}")
                raise ValueError("artifact archive has a damaged optional entry")
    except (
        zipfile.BadZipFile,
        EOFError,
        RuntimeError,
        OSError,
        zlib.error,
        NotImplementedError,
        UnicodeError,
    ):
        # ZIP exceptions can contain attacker-controlled optional entry names.
        raise ValueError("artifact archive is corrupt or incomplete") from None


def _list_all(
    url: str,
    collection_key: str,
    token: str,
    fetch_page=None,
    budget: _RuntimeBudget | None = None,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    while url:
        payload, next_url = _fetch_metadata_page(url, token, fetch_page, budget)
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


def _actions_run_url(api_url: str, repository: str, run_id: int) -> str:
    """Build the web URL for an Actions run from the configured GitHub API host."""
    parsed_api_url = urlsplit(api_url)
    api_host = parsed_api_url.hostname
    if not api_host:
        raise ValueError("GitHub API URL must include a host")
    if api_host.lower() == "api.github.com":
        web_host = "github.com"
    else:
        web_host = f"[{api_host}]" if ":" in api_host else api_host
        if parsed_api_url.port:
            web_host += f":{parsed_api_url.port}"
    return f"https://{web_host}/{repository}/actions/runs/{run_id}"


def monitor_repository(
    repository: str,
    api_url: str,
    token: str,
    *,
    now: datetime | None = None,
    fetch_page=None,
    open_url=None,
    budget: _RuntimeBudget | None = None,
) -> int:
    """Fail if a successful Pages run loses its evidence inside the 90-day window."""
    budget = budget or _RuntimeBudget(MONITOR_RUNTIME_BUDGET_SECONDS)
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
    runs = _list_all(runs_url, "workflow_runs", token, fetch_page, budget)
    checked = 0
    failures: list[str] = []

    for run in runs:
        if run.get("conclusion") != "success":
            continue
        run_id = run.get("id")
        commit = run.get("head_sha")
        has_numeric_run_id = type(run_id) is int and run_id > 0
        run_link = (
            f" | GitHub Actions: {_actions_run_url(api_url, repository, run_id)}"
            if has_numeric_run_id
            else ""
        )
        try:
            run_created_at = parse_timestamp(
                run.get("created_at"), "workflow run created_at"
            )
        except ValueError as error:
            failures.append(
                f"run {run_id if has_numeric_run_id else 'unknown'} | "
                f"commit {commit if isinstance(commit, str) and commit else 'unknown'} | "
                f"review deadline unknown: {error}{run_link}"
            )
            continue
        deadline = run_created_at + REQUIRED_RETENTION
        if deadline <= current_time:
            continue
        if not has_numeric_run_id or not isinstance(commit, str) or not commit:
            failures.append(
                f"run {run_id if has_numeric_run_id else 'unknown'} | "
                f"commit {commit if isinstance(commit, str) and commit else 'unknown'} | "
                f"review deadline {deadline.isoformat()}: "
                "successful Pages run is missing a numeric id or commit SHA"
                f"{run_link}"
            )
            continue

        if budget.remaining() <= 0:
            failures.append(
                f"run {run_id} | commit {commit} | "
                f"review deadline {deadline.isoformat()}: evidence not checked; "
                f"shared monitor time budget exhausted after "
                f"{budget.seconds:g} seconds{run_link}"
            )
            continue

        try:
            compare_url = (
                f"{api_url.rstrip('/')}/repos/{repository}/compare/"
                f"{RETENTION_POLICY_COMMIT}...{quote(commit, safe='')}"
            )
            comparison, _ = _fetch_metadata_page(
                compare_url, token, fetch_page, budget
            )
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
                artifacts_url, "artifacts", token, fetch_page, budget
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
                    retry_count = verify_artifact_download(
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
                        budget=budget,
                    )
                    if retry_count:
                        retry_label = "retry" if retry_count == 1 else "retries"
                        print(
                            f"Recovered artifact download after {retry_count} "
                            f"{retry_label} (run {run_id}, artifact "
                            f"{expected_name}, ID {artifact_id})."
                        )
                except (OSError, TimeoutError, ValueError) as error:
                    if isinstance(error, _RetryBudgetExceeded):
                        raise
                    errors.append(str(error))
                    budget.ensure_available()
                else:
                    break
            else:
                raise ValueError(
                    f"validation artifact is invalid or unavailable: {'; '.join(errors)}"
                )
        except (OSError, TimeoutError, ValueError) as error:
            detail = (
                f"evidence not checked; {error}"
                if isinstance(error, _RetryBudgetExceeded)
                else str(error)
            )
            failures.append(
                f"run {run_id} | commit {commit} | "
                f"review deadline {deadline.isoformat()}: {detail}{run_link}"
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
