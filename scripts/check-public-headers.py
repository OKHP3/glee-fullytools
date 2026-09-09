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

# These are the controls that the portable policy is expected to deliver in
# addition to the presence of the CSP header itself.  Hash sources are
# generated and may change; the stable source/framing/resource boundaries are
# what this live smoke test can safely assert.
REQUIRED_CSP_TOKENS = {
    "script-src": ("'self'",),
    "script-src-attr": ("'none'",),
    "frame-src": ("'self'", "https://okhp3.github.io"),
    "object-src": ("'none'",),
    "base-uri": ("'self'",),
    "form-action": ("'self'",),
    "manifest-src": ("'self'",),
    "upgrade-insecure-requests": (),
}


def parse_csp(value: str) -> dict[str, set[str]]:
    """Return CSP directives and their source tokens from one header value."""
    directives: dict[str, set[str]] = {}
    for raw_directive in value.split(";"):
        tokens = raw_directive.split()
        if not tokens:
            continue
        name, *sources = tokens
        directives[name.lower()] = set(sources)
    return directives


def csp_checks(value: str) -> list[tuple[str, bool, str]]:
    """Check stable CSP boundaries without depending on generated hashes."""
    directives = parse_csp(value)
    checks: list[tuple[str, bool, str]] = []
    for directive, expected_tokens in REQUIRED_CSP_TOKENS.items():
        sources = directives.get(directive)
        if sources is None:
            checks.append((directive, False, "directive missing"))
            continue
        missing = [token for token in expected_tokens if token not in sources]
        if missing:
            checks.append((directive, False, f"missing {' '.join(missing)}"))
            continue
        if directive == "script-src" and "'unsafe-inline'" in sources:
            checks.append(
                (directive, False, "must not contain 'unsafe-inline'")
            )
            continue
        checks.append((directive, True, "expected controls present"))
    return checks

def fetch_headers(url: str, timeout: float) -> dict[str, str]:
    request = Request(
        url,
        method="GET",
        headers={"User-Agent": "Glee-fully-Pages-Header-Smoke/1"},
    )
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

    csp = headers.get("content-security-policy")
    if csp:
        print("  CSP directive checks:")
        csp_failures = []
        for directive, passed, detail in csp_checks(csp):
            print(f"    {'OK' if passed else 'FAIL'} {directive}: {detail}")
            if not passed:
                csp_failures.append(directive)
    else:
        print("  CSP directive checks: NOT RUN (Content-Security-Policy missing)")
        csp_failures = list(REQUIRED_CSP_TOKENS)

    observed = sorted(
        name for name in headers if name in REQUIRED_HEADERS
    )
    missing = [name for name in REQUIRED_HEADERS if name not in headers]
    print(f"  observed required headers: {len(observed)}/{len(REQUIRED_HEADERS)}")
    if missing:
        print("  Missing headers are host-delivery findings, not proof that _headers was read.")
        return 1
    if csp_failures:
        print("  CSP control failures are host-delivery findings.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
