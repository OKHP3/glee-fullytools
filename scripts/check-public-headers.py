#!/usr/bin/env python3
"""Smoke-test security headers delivered by the public Pages host.

This intentionally checks the live response rather than reading `_headers`.
GitHub Pages does not consume that file, so a missing header is meaningful
evidence even when the portable policy is correctly authored.
"""

from __future__ import annotations

import argparse
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REQUIRED_HEADERS = {
    "strict-transport-security": "transport enforcement (HSTS)",
    "content-security-policy": "script/resource policy (CSP)",
    "x-frame-options": "framing protection",
    "x-content-type-options": "MIME sniffing protection",
}


def fetch_headers(url: str, timeout: float) -> dict[str, str]:
    request = Request(url, method="HEAD", headers={"User-Agent": "Glee-fully-Pages-Header-Smoke/1"})
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        return {key.lower(): value for key, value in exc.headers.items()}
    return {key.lower(): value for key, value in response.headers.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://glee-fully.tools/", help="public URL to inspect")
    parser.add_argument("--timeout", type=float, default=20, help="request timeout in seconds")
    args = parser.parse_args()

    try:
        headers = fetch_headers(args.url, args.timeout)
    except (URLError, TimeoutError, OSError) as exc:
        print(f"Header smoke test could not reach {args.url}: {exc}", file=sys.stderr)
        return 2

    print(f"Header smoke test: {args.url}")
    for name, purpose in REQUIRED_HEADERS.items():
        value = headers.get(name)
        print(f"  {'OK' if value else 'MISSING'} {name}: {value or 'not delivered'} ({purpose})")

    observed = sorted(
        name for name in headers if name in REQUIRED_HEADERS
    )
    missing = [name for name in REQUIRED_HEADERS if name not in headers]
    print(f"  observed required headers: {len(observed)}/{len(REQUIRED_HEADERS)}")
    if missing:
        print("  Missing headers are host-delivery findings, not proof that _headers was read.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())