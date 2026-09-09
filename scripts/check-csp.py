#!/usr/bin/env python3
"""CI guard against missing, drifted, or weakened page CSP policies."""
import runpy
import sys

from csp import inline_markup_violations, tracked_html


if __name__ == "__main__":
    sys.argv = ["scripts/generate-csp.py", "--check"]
    runpy.run_path("scripts/generate-csp.py", run_name="__main__")
    violations = [
        violation
        for page in tracked_html()
        for violation in inline_markup_violations(page)
    ]
    if violations:
        print("Unsupported inline executable markup found:")
        print("\n".join(violations))
        raise SystemExit(1)
    print(f"Inline executable markup check passed for {len(tracked_html())} HTML files.")
