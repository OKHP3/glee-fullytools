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

Scanning passes
---------------
Pass 1 — HTML files: inline style= attributes and known utility class names.
Pass 2 — CSS files:  class rules in theme.css (and any other project CSS)
          that set `color` to an accent token/hex on a risky element selector.

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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACCENT_HEX_PATTERN = re.compile(
    r"#(?:d94f63|d35b2d)", re.IGNORECASE
)

ACCENT_VAR_PATTERN = re.compile(
    r"var\(\s*--color-(?:accent|rust)\s*[,)]", re.IGNORECASE
)

# Matches a text `color:` declaration (not background-color / border-color)
# pointing to an accent hex or accent CSS variable.
ACCENT_TEXT_COLOR_RE = re.compile(
    r"(?<![a-z-])color\s*:\s*"
    r"(var\(\s*--color-(?:accent|rust)\b[^;]*|#(?:d94f63|d35b2d)\b)",
    re.IGNORECASE,
)

# Matches background-color or border-color (used to exclude those properties)
BG_BORDER_RE = re.compile(r"(background|border)-color", re.IGNORECASE)

# CSS variable definition line (--foo: ...) — not a text-color usage
CSS_VAR_DEF_RE = re.compile(r"^\s*--")

# Bold font-weight in the same rule block → bold text passes AA at >=14 px
BOLD_WEIGHT_RE = re.compile(r"font-weight\s*:\s*(bold|bolder|[6-9]\d\d)", re.IGNORECASE)

# CSS utility classes known to apply accent color to text
ACCENT_TEXT_CLASSES = {"text-accent", "link-accent"}

# Tags where accent color on text is safe (large/interactive controls)
SAFE_TAGS = {
    "button", "a",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "span",
}

# Tags where accent color on text is risky (normal body text containers)
RISKY_TAGS = {
    "p", "li", "td", "th", "dd", "dt", "figcaption", "blockquote",
    "label", "caption", "small", "em", "strong",
}

# Directories to skip when walking the project tree
SKIP_DIRS = {
    ".pythonlibs", ".cache", ".local", "node_modules",
    ".git", "attached_assets", ".agents",
}

# CSS files to scan (relative to repo root)
CSS_FILES = [Path("assets/css/theme.css")]


# ---------------------------------------------------------------------------
# CSS utilities
# ---------------------------------------------------------------------------

def extract_final_element(selector: str) -> str | None:
    """
    Return the final element type from a CSS selector, or None if the
    selector is class/id/attribute-only (no element type to match on).

    Examples:
      '.glee-main p'            -> 'p'
      '.keep-exploring__name'   -> None
      'body:not(.glee) p.bold'  -> 'p'
      '.foo a > em:first-child' -> 'em'
    """
    s = selector
    # Strip pseudo-elements (::before, ::after, …)
    s = re.sub(r"::[a-zA-Z-]+", "", s)
    # Strip pseudo-classes with parens (:not(…), :nth-child(…), …)
    s = re.sub(r":[a-zA-Z-]+\([^)]*\)", "", s)
    # Strip remaining simple pseudo-classes (:hover, :focus, …)
    s = re.sub(r":[a-zA-Z-]+", "", s)
    # Strip attribute selectors ([attr=val])
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = s.strip()

    # Split on combinators and inspect last token
    for seg in reversed(re.split(r"[\s>~+]+", s)):
        seg = seg.strip()
        m = re.match(r"^([a-zA-Z][a-zA-Z0-9]*)", seg)
        if m:
            return m.group(1).lower()

    return None


def extract_css_rules(css_text: str):
    """
    Yield (selector_str, declarations_str, start_lineno) for every CSS rule
    block in *css_text*, recursing into @media and other at-rules.

    Block comments are stripped (with line-count preserved) before parsing.
    """
    # Strip block comments but keep newlines so line numbers stay accurate
    clean = re.sub(
        r"/\*.*?\*/",
        lambda m: "\n" * m.group(0).count("\n"),
        css_text,
        flags=re.DOTALL,
    )

    def _process(text: str, base_line: int = 1):
        n = len(text)
        j = 0
        while j < n:
            # Skip leading whitespace
            while j < n and text[j] in " \t\n\r":
                j += 1
            if j >= n:
                break

            brace = text.find("{", j)
            if brace == -1:
                break

            selector = text[j:brace].strip()
            # Line number = base + newlines before this opening brace
            lineno = base_line + text[:brace].count("\n")

            # Find the matching closing brace
            depth, k = 1, brace + 1
            while k < n and depth > 0:
                if text[k] == "{":
                    depth += 1
                elif text[k] == "}":
                    depth -= 1
                k += 1

            content = text[brace + 1 : k - 1]

            if selector.lstrip().startswith("@"):
                # At-rule: recurse so inner rules are checked
                yield from _process(content, lineno)
            elif selector:
                yield selector, content, lineno

            j = k

    yield from _process(clean)


# ---------------------------------------------------------------------------
# Pass 1 — HTML scanning
# ---------------------------------------------------------------------------

def scan_html_file(path: Path) -> list[dict]:
    """Return advisory findings for one HTML file (inline styles + utility classes)."""
    findings = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return findings

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("<!--"):
            continue

        # 1a. Inline style= with accent hex as text color
        if "style=" in line and ACCENT_HEX_PATTERN.search(line):
            if re.search(r"(?<!\w)color\s*:\s*(?:#d94f63|#d35b2d)", line, re.IGNORECASE):
                tag_m = re.search(r"<(\w+)\b", line)
                tag = tag_m.group(1).lower() if tag_m else "unknown"
                severity = "ADVISORY" if tag in RISKY_TAGS else "INFO"
                findings.append({
                    "file": str(path),
                    "line": lineno,
                    "severity": severity,
                    "tag": tag,
                    "rule": "inline-style-accent-color",
                    "detail": (
                        f"<{tag}> has inline accent color -- "
                        f"verify it is large/bold text (>=18.67 px normal "
                        f"or >=14 px bold)."
                    ),
                    "snippet": stripped[:120],
                })

        # 1b. Inline style= with accent var as text color
        if "style=" in line and ACCENT_VAR_PATTERN.search(line):
            if re.search(
                r"(?<!\w)color\s*:\s*var\(--color-(?:accent|rust)", line, re.IGNORECASE
            ):
                tag_m = re.search(r"<(\w+)\b", line)
                tag = tag_m.group(1).lower() if tag_m else "unknown"
                if tag in RISKY_TAGS:
                    findings.append({
                        "file": str(path),
                        "line": lineno,
                        "severity": "ADVISORY",
                        "tag": tag,
                        "rule": "inline-style-accent-var",
                        "detail": (
                            f"<{tag}> uses var(--color-accent/rust) as text color -- "
                            f"accent tokens are below 4.5:1 for normal body text."
                        ),
                        "snippet": stripped[:120],
                    })

        # 1c. Utility classes that apply accent color to text
        for cls in ACCENT_TEXT_CLASSES:
            if 'class="' in line and cls in line:
                tag_m = re.search(r"<(\w+)\b", line)
                tag = tag_m.group(1).lower() if tag_m else "unknown"
                if tag in RISKY_TAGS:
                    findings.append({
                        "file": str(path),
                        "line": lineno,
                        "severity": "ADVISORY",
                        "tag": tag,
                        "rule": f"utility-class-{cls}",
                        "detail": (
                            f"<{tag}> uses .{cls} -- verify it meets "
                            f"large/bold text threshold."
                        ),
                        "snippet": stripped[:120],
                    })

    return findings


# ---------------------------------------------------------------------------
# Pass 2 — CSS rule scanning
# ---------------------------------------------------------------------------

def scan_css_file(path: Path) -> list[dict]:
    """
    Return advisory findings for CSS rule blocks in *path* that set `color`
    to an accent token/hex on a selector targeting a risky element type.

    Exemptions (downgraded to INFO):
    - `border-color` and `background-color` declarations are ignored.
    - CSS custom-property definitions (--foo: ...) are ignored.
    - If the same rule block also declares a bold font-weight (600+/bold),
      the finding is INFO not ADVISORY, because bold text at >=14 px passes
      WCAG AA for these accent colors.
    """
    try:
        css_text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings = []

    for selector_raw, declarations, lineno in extract_css_rules(css_text):
        # Check every declaration line for a text-color accent usage
        decl_lines = [dl.strip() for dl in declarations.splitlines() if dl.strip()]
        has_accent_text_color = any(
            ACCENT_TEXT_COLOR_RE.search(dl)
            and not BG_BORDER_RE.search(dl)
            and not CSS_VAR_DEF_RE.match(dl)
            for dl in decl_lines
        )
        if not has_accent_text_color:
            continue

        # Does this rule block also declare a bold font weight?
        is_bold_rule = bool(BOLD_WEIGHT_RE.search(declarations))

        # Inspect each comma-separated selector part
        for sel_part in selector_raw.split(","):
            sel_part = sel_part.strip()
            if not sel_part:
                continue

            element = extract_final_element(sel_part)
            if element is None:
                continue  # class/id/attribute-only selector — skip

            if element in RISKY_TAGS:
                # Bold-weight in same block means body-text threshold met
                # (bold >=14 px passes WCAG AA for these accent ratios)
                severity = "INFO" if is_bold_rule else "ADVISORY"
                findings.append({
                    "file": str(path),
                    "line": lineno,
                    "severity": severity,
                    "selector": sel_part,
                    "tag": element,
                    "rule": "css-rule-accent-color",
                    "detail": (
                        f"CSS rule '{sel_part}' targets <{element}> with accent color"
                        + (" (bold-weight in same block — INFO only)." if is_bold_rule
                           else " -- verify this element is always large/bold text "
                                "(>=18.67 px normal or >=14 px bold).")
                    ),
                    "snippet": f"{sel_part[:70]} {{ color: <accent>; }}",
                })

    return findings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    strict = "--strict" in sys.argv

    root = Path(".")
    all_findings: list[dict] = []

    # Pass 1: HTML files
    html_scanned = 0
    for path in sorted(root.rglob("*.html")):
        if any(s in path.parts for s in SKIP_DIRS):
            continue
        all_findings.extend(scan_html_file(path))
        html_scanned += 1

    # Pass 2: CSS files
    css_scanned = 0
    for css_path in CSS_FILES:
        if not css_path.exists():
            continue
        # Also pick up any other project CSS outside assets/templates
        all_findings.extend(scan_css_file(css_path))
        css_scanned += 1

    # Additionally scan any other .css files in the project (excluding skip dirs)
    css_paths_seen = {p.resolve() for p in CSS_FILES}
    for path in sorted(root.rglob("*.css")):
        if any(s in path.parts for s in SKIP_DIRS):
            continue
        if path.resolve() in css_paths_seen:
            continue
        all_findings.extend(scan_css_file(path))
        css_scanned += 1
        css_paths_seen.add(path.resolve())

    # Separate by severity
    advisories = [f for f in all_findings if f["severity"] == "ADVISORY"]
    infos      = [f for f in all_findings if f["severity"] == "INFO"]

    # Write machine-readable output
    out_dir = Path("assets/audit")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "generated": "2026-05-28",
        "html_files_scanned": html_scanned,
        "css_files_scanned": css_scanned,
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
        "passes": [
            "Pass 1 — HTML inline style= attributes and utility class names",
            "Pass 2 — CSS rule blocks in project stylesheet(s)",
        ],
    }
    out_path = out_dir / "accent-contrast-report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Human-readable output
    print("Accent contrast advisory scan")
    print(f"  HTML files scanned : {html_scanned}")
    print(f"  CSS files scanned  : {css_scanned}")
    print(f"  Advisories         : {len(advisories)}")
    print(f"  Info notes         : {len(infos)}")
    print(f"  Report             : {out_path}")

    if advisories:
        print("\nAdvisories (accent color on body-text elements):")
        for f in advisories:
            loc = f.get("selector") or f.get("tag", "unknown")
            print(f"  [ADVISORY] {f['file']}:{f['line']} — {loc}")
            print(f"    Rule   : {f['rule']}")
            print(f"    Detail : {f['detail']}")
            print(f"    Snippet: {f['snippet']}")
            print()
    else:
        print("\n  No body-text accent color violations found.")

    if infos:
        print("Info notes (context-dependent -- review manually):")
        for f in infos:
            loc = f.get("selector") or f.get("tag", "unknown")
            print(f"  [INFO] {f['file']}:{f['line']} {loc} -- {f['rule']}")

    print()
    print("This script is advisory only. Exit 0 regardless of findings.")
    print("Use --strict to exit 1 on any advisory (for manual gate use).")

    if strict and advisories:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
