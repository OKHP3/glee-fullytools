#!/usr/bin/env python3
"""CI guard against missing, drifted, or weakened page CSP policies."""
import runpy
import sys

from csp import inline_markup_violations, tracked_html


if __name__ == "__main__":
    sys.argv = ["scripts/generate-csp.py", "--check"]
    status = runpy.run_path("scripts/generate-csp.py")["main"]()
    if status:
        raise SystemExit(status)
    pages = tracked_html()
    violations = [
        violation
        for page in pages
        for violation in inline_markup_violations(page)
    ]
    if violations:
        print("Unsupported inline executable markup found:")
        print("\n".join(violations))
        raise SystemExit(1)
    print(f"Inline executable markup check passed for {len(pages)} HTML files.")
