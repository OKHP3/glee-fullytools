#!/usr/bin/env python3
"""
check-accent-contrast.py
Advisory scanner: flags uses of accent colors on body-text elements.

Background
----------
The glee-fully.tools accent colors (#d94f63, #d35b2d) sit at 3.37-3.55:1
contrast against the paper background (#f6f2ee). They pass WCAG 2.1 AA for
large/bold text (>=18.67 px normal, >=14 px bold) but fail for normal-weight
body text at default size.

Editorial rule (from assets/docs/gleefully-replit-theme-guide.md):
  var(--color-accent) must not be used as the sole color signal for
  normal-weight body text smaller than 18.67 px.

This script scans HTML files for patterns that could violate that rule.
It exits 0 and reports findings as advisories only -- it does not block CI.
Run it during code review when adding or changing colored text.

Usage
-----
  python3 scripts/check-accent-contrast.py [--strict]

  --strict  Exit 1 if any advisory findings are found (for manual gate use).

Output
------
  Prints a structured advisory report.
  Writes machine-readable JSON to assets/audit/accent-contrast-report.json.
"""

import re
import sys
import json
from pathlib import Path

# Accent colors that have insufficient contrast for normal body text
ACCENT_HEXES = {"#d94f63", "#d35b2d"}
ACCENT_HEX_PATTERN = re.compile(
    r"#(?:d94f63|d35b2d|D94F63|D35B2D)", re.IGNORECASE
)

# CSS variable references that resolve to accent colors
ACCENT_VAR_PATTERN = re.compile(
    r"var\(\s*--color-(?:accent|rust)\s*[,)]", re.IGNORECASE
)

# CSS utility classes known to apply accent color to text
ACCENT_TEXT_CLASSES = {"text-accent", "link-accent"}

# Elements where accent color on text is safe (buttons, headings, UI controls)
SAFE_TAGS = {
    "button", "a",           # interactive controls
    "h1", "h2", "h3",        # headings (usually large text)
    "span",                  # allowed inline -- context-dependent, flag as info
}

# Tags where accent color on text is risky (normal body text containers)
RISKY_TAGS = {"p", "li", "td", "th", "dd", "dt", "figcaption", "blockquote",
              "label", "caption", "small", "em", "strong"}

# Directories to skip
SKIP_DIRS = {
    ".pythonlibs", ".cache", ".local", "node_modules",
    ".git", "attached_assets", ".agents", "assets",
}


def scan_file(path: Path) -> list[dict]:
    """Return a list of advisory findings for one HTML file."""
    findings = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
    except Exception:
        return findings

    for lineno, line in enumerate(lines, 1):
        # Skip comment lines
        stripped = line.strip()
        if stripped.startswith("<!--"):
            continue

        # 1. Inline style with accent color on a risky tag
        if 'style=' in line and ACCENT_HEX_PATTERN.search(line):
            # Heuristic: extract the tag name
            tag_m = re.search(r'<(\w+)\b', line)
            tag = tag_m.group(1).lower() if tag_m else "unknown"
            # Check if color property (not background-color)
            if re.search(r'(?<!\w)color\s*:\s*(?:#d94f63|#d35b2d)', line, re.IGNORECASE):
                severity = "ADVISORY" if tag in RISKY_TAGS else "INFO"
                findings.append({
                    "file": str(path),
                    "line": lineno,
                    "severity": severity,
                    "tag": tag,
                    "rule": "inline-style-accent-color",
                    "detail": f"<{tag}> has inline accent color -- "
                              f"verify it is large/bold text (>=18.67 px normal "
                              f"or >=14 px bold).",
                    "snippet": stripped[:120],
                })

        # 2. CSS var(--color-accent) or var(--color-rust) used as text color
        if 'style=' in line and ACCENT_VAR_PATTERN.search(line):
            if re.search(r'(?<!\w)color\s*:\s*var\(--color-(?:accent|rust)', line, re.IGNORECASE):
                tag_m = re.search(r'<(\w+)\b', line)
                tag = tag_m.group(1).lower() if tag_m else "unknown"
                if tag in RISKY_TAGS:
                    findings.append({
                        "file": str(path),
                        "line": lineno,
                        "severity": "ADVISORY",
                        "tag": tag,
                        "rule": "inline-style-accent-var",
                        "detail": f"<{tag}> uses var(--color-accent/rust) as text color -- "
                                  f"accent tokens are below 4.5:1 for normal body text.",
                        "snippet": stripped[:120],
                    })

        # 3. Utility classes that apply accent color to text
        for cls in ACCENT_TEXT_CLASSES:
            if f'class="' in line and cls in line:
                tag_m = re.search(r'<(\w+)\b', line)
                tag = tag_m.group(1).lower() if tag_m else "unknown"
                if tag in RISKY_TAGS:
                    findings.append({
                        "file": str(path),
                        "line": lineno,
                        "severity": "ADVISORY",
                        "tag": tag,
                        "rule": f"utility-class-{cls}",
                        "detail": f"<{tag}> uses .{cls} -- verify it meets "
                                  f"large/bold text threshold.",
                        "snippet": stripped[:120],
                    })

    return findings


def main() -> int:
    strict = "--strict" in sys.argv

    root = Path(".")
    all_findings = []
    files_scanned = 0

    for path in sorted(root.rglob("*.html")):
        if any(s in path.parts for s in SKIP_DIRS):
            continue
        findings = scan_file(path)
        all_findings.extend(findings)
        files_scanned += 1

    # Separate by severity
    advisories = [f for f in all_findings if f["severity"] == "ADVISORY"]
    infos      = [f for f in all_findings if f["severity"] == "INFO"]

    # Write machine-readable output
    out_dir = Path("assets/audit")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "generated": "2026-05-27",
        "files_scanned": files_scanned,
        "advisory_count": len(advisories),
        "info_count": len(infos),
        "findings": all_findings,
        "rule": (
            "var(--color-accent) (#d94f63 / #d35b2d) must not be used as the sole "
            "color signal for normal-weight body text smaller than 18.67 px. "
            "Contrast ratios: #d94f63 = 3.37:1, #d35b2d = 3.55:1 (paper bg #f6f2ee). "
            "Passes WCAG 2.1 AA for large/bold text (>=18.67px normal or >=14px bold) "
            "but fails for normal body text."
        ),
    }
    out_path = out_dir / "accent-contrast-report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Human-readable output
    print(f"Accent contrast advisory scan")
    print(f"  Files scanned : {files_scanned}")
    print(f"  Advisories    : {len(advisories)}")
    print(f"  Info notes    : {len(infos)}")
    print(f"  Report        : {out_path}")

    if advisories:
        print("\nAdvisories (accent color on body-text elements):")
        for f in advisories:
            print(f"  [{f['severity']}] {f['file']}:{f['line']}")
            print(f"    Rule   : {f['rule']}")
            print(f"    Detail : {f['detail']}")
            print(f"    Snippet: {f['snippet']}")
            print()
    else:
        print("\n  No body-text accent color violations found.")

    if infos:
        print(f"Info notes (context-dependent -- review manually):")
        for f in infos:
            print(f"  [INFO] {f['file']}:{f['line']} <{f['tag']}> -- {f['rule']}")

    print()
    print("This script is advisory only. Exit 0 regardless of findings.")
    print("Use --strict to exit 1 on any advisory (for manual gate use).")

    if strict and advisories:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
