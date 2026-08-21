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

Task #26 introduced a dark-mode palette (--bg #1a1210, --color-accent #f07585)
where the lightened coral reaches 4.9:1 against the dark surface (#241c1a),
passing WCAG AA for all text sizes. This script checks BOTH modes and reports
contrast ratios for each so regressions in either direction are caught.

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

  --strict  Exit 1 if any advisory findings or hover-state failures are found.

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
# WCAG contrast-ratio math
# ---------------------------------------------------------------------------

def _srgb_linearize(c: int) -> float:
    s = c / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return (
        0.2126 * _srgb_linearize(r)
        + 0.7152 * _srgb_linearize(g)
        + 0.0722 * _srgb_linearize(b)
    )


def contrast_ratio(fg: str, bg: str) -> float:
    """Return WCAG contrast ratio (>=1.0) between two hex colors."""
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def wcag_aa_normal(ratio: float) -> bool:
    return ratio >= 4.5


def wcag_aa_large(ratio: float) -> bool:
    return ratio >= 3.0


# ---------------------------------------------------------------------------
# Mode palettes
# ---------------------------------------------------------------------------

# Light-mode palette (Glee-fully paper theme)
LIGHT_MODE = {
    "bg":           "#f6f2ee",
    "surface":      "#f6f2ee",
    "accent_hex":   ["#d94f63", "#d35b2d"],   # coral, rust
}

# Dark-mode defaults (Task #26; overridden by parse_dark_mode_tokens if found)
_DARK_MODE_DEFAULTS = {
    "bg":           "#1a1210",
    "surface":      "#241c1a",
    "accent_hex":   ["#f07585"],              # lightened coral
}


def parse_dark_mode_tokens(theme_css_path: Path) -> dict:
    """
    Read the first `@media (prefers-color-scheme: dark) { .glee-main { … } }`
    block in theme.css and extract --color-bg, --color-surface, --color-accent.

    Falls back to _DARK_MODE_DEFAULTS for any token not found.
    """
    result = dict(_DARK_MODE_DEFAULTS)
    if not theme_css_path.exists():
        return result

    text = theme_css_path.read_text(encoding="utf-8", errors="ignore")

    # Find the token-layer block: @media dark { .glee-main { --color-bg: … } }
    # We look for the first @media block that contains `--color-accent` override.
    dark_block_re = re.compile(
        r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)"
        r"\s*\{(.*?)\}",
        re.DOTALL | re.IGNORECASE,
    )

    for m in dark_block_re.finditer(text):
        block = m.group(1)
        # Only care about blocks that touch Glee token overrides
        if "--color-accent" not in block:
            continue
        # Extract token values
        bg_m      = re.search(r"--color-bg\s*:\s*(#[0-9a-fA-F]{3,6})", block)
        surf_m    = re.search(r"--color-surface\s*:\s*(#[0-9a-fA-F]{3,6})", block)
        accent_m  = re.search(r"--color-accent\s*:\s*(#[0-9a-fA-F]{3,6})", block)

        if bg_m:
            result["bg"] = bg_m.group(1)
        if surf_m:
            result["surface"] = surf_m.group(1)
        if accent_m:
            result["accent_hex"] = [accent_m.group(1)]
        break  # first matching block is the canonical token layer

    return result


def parse_okh_root_tokens(theme_css_path: Path) -> dict:
    """Extract OKH default dark-mode surface colors from the bare :root {…} block
    in theme.css.

    The OKH default palette lives in :root (not inside any dark-mode at-rule):
      --okh-espresso: #2a2320   → resolved value of --color-bg: var(--okh-espresso)
      --color-surface: #111827

    One level of var() indirection is resolved: if --color-bg refers to
    var(--okh-espresso) the function follows the alias to the raw hex.

    Returns {"bg": <hex>, "surface": <hex>}.  Falls back to
    _OKH_DARK_SURFACE_DEFAULTS for any token not found or if the file is absent.
    """
    result = dict(_OKH_DARK_SURFACE_DEFAULTS)
    if not theme_css_path.exists():
        return result

    text = theme_css_path.read_text(encoding="utf-8", errors="ignore")

    # Match the bare :root { … } block — not :root[data-theme="…"] variants.
    # Use a negative lookbehind to skip :root[…] and :root.foo selectors.
    root_open_re = re.compile(r"(?<![a-zA-Z0-9\[\]\"'_\-]):root\s*\{", re.IGNORECASE)
    m = root_open_re.search(text)
    if not m:
        return result

    # Walk forward to find the matching closing brace
    depth, i, n = 1, m.end(), len(text)
    while i < n and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    block = text[m.end() : i - 1]

    # Collect all bare-hex token definitions: --foo: #rrggbb
    token_values: dict = {}
    for tok_m in re.finditer(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\b", block):
        token_values[tok_m.group(1)] = tok_m.group(2)

    # Collect single-level var() references: --foo: var(--bar)
    var_refs: dict = {}
    for ref_m in re.finditer(r"--([\w-]+)\s*:\s*var\(\s*--([\w-]+)\s*\)", block):
        var_refs[ref_m.group(1)] = ref_m.group(2)

    # Resolve --color-bg → may be var(--okh-espresso) or a direct hex
    bg_hex = token_values.get("color-bg")
    if not bg_hex:
        ref = var_refs.get("color-bg")
        if ref:
            bg_hex = token_values.get(ref)
    if bg_hex:
        result["bg"] = bg_hex

    # --color-surface is a direct hex in :root
    surface_hex = token_values.get("color-surface")
    if surface_hex:
        result["surface"] = surface_hex

    return result


# Live-parsed at import time so any caller (tests, imports) sees real CSS tokens.
# main() re-parses to pick up a --theme-css CLI override if provided.
DARK_MODE = parse_dark_mode_tokens(Path("assets/css/theme.css"))


def _worst_light_contrast(fg_hex: str) -> float:
    """Lowest contrast the fg hex achieves against any light-mode surface."""
    return min(
        contrast_ratio(fg_hex, LIGHT_MODE["bg"]),
        contrast_ratio(fg_hex, LIGHT_MODE["surface"]),
    )


def _worst_dark_contrast(fg_hex: str) -> float:
    """Lowest contrast the fg hex achieves against any dark-mode surface."""
    return min(
        contrast_ratio(fg_hex, DARK_MODE["bg"]),
        contrast_ratio(fg_hex, DARK_MODE["surface"]),
    )


def _worst_accent_light() -> tuple:
    """(worst_ratio, which_hex) across all light-mode accent hexes."""
    pairs = [(_worst_light_contrast(h), h) for h in LIGHT_MODE["accent_hex"]]
    return min(pairs, key=lambda x: x[0])


def _worst_accent_dark() -> tuple:
    """(worst_ratio, which_hex) across all dark-mode accent hexes."""
    pairs = [(_worst_dark_contrast(h), h) for h in DARK_MODE["accent_hex"]]
    return min(pairs, key=lambda x: x[0])


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

# Bold font-weight in the same rule block (prerequisite for INFO downgrade)
BOLD_WEIGHT_RE = re.compile(r"font-weight\s*:\s*(bold|bolder|[6-9]\d\d)", re.IGNORECASE)

# Explicit font-size in the same rule block — extracts the numeric value in rem/px/pt
# Used alongside BOLD_WEIGHT_RE to confirm the qualifying threshold is provably met.
# Rule: bold text >= 14 px passes WCAG AA at these accent contrast ratios.
FONT_SIZE_RE = re.compile(
    r"font-size\s*:\s*([\d.]+)(rem|em|px|pt)\b", re.IGNORECASE
)

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

# These are the static hover states whose backgrounds are known from the
# page skins.  They are intentionally explicit rather than attempting to
# emulate the browser cascade: this is a small regression gate for the
# user-visible states that have previously failed WCAG contrast.
HOVER_CONTRAST_CHECKS = (
    {
        "name": "Glee breadcrumb hover (light)",
        "selector": ".glee-breadcrumb-item a:hover",
        "mode": "light",
        "background": "#f6f2ee",
        "required": True,
    },
    {
        "name": "Glee footer link hover (light)",
        "selector": "html[data-theme=\"light\"] .glee-main .footer-column a:hover",
        "mode": "light",
        "background": "#fff7f1",
        "required": True,
    },
    {
        "name": "Glee breadcrumb hover (dark)",
        "selector": "html[data-color-scheme=\"dark\"] .glee-breadcrumb-item a:hover",
        "mode": "dark",
        "background": "#241c1a",
        "required": True,
    },
    {
        "name": "Glee footer link hover (dark)",
        "selector": "html[data-color-scheme=\"dark\"] .glee-main .footer-column a:hover",
        "mode": "dark",
        "background": "#1a1816",
        "required": True,
    },
    {
        "name": "AskJamie footer link hover (light)",
        "selector": ".askjamie-main .site-footer a:hover",
        "mode": "light",
        "background": "#f7f3ee",
        "required": True,
    },
    {
        "name": "AskJamie footer link hover (dark)",
        "selector": "html[data-color-scheme=\"dark\"] .askjamie-main .site-footer a:hover",
        "mode": "dark",
        "background": "#1e1b18",
        "required": True,
    },
)

_HOVER_HEX_COLOR_RE = re.compile(
    r"(?<![a-z-])color\s*:\s*(#[0-9a-fA-F]{3,6})\b", re.IGNORECASE
)
_HOVER_VAR_COLOR_RE = re.compile(
    r"(?<![a-z-])color\s*:\s*var\(\s*--color-accent\b[^)]*\)",
    re.IGNORECASE,
)


def scan_hover_contrast(path: Path) -> list[dict]:
    """Check the known Glee and AskJamie hover states against their surfaces.

    A missing rule is also a finding.  That prevents a future cleanup from
    silently removing a state-specific color and letting an unrelated,
    low-contrast inherited value win in the cascade.
    """
    try:
        css_text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    rules = list(extract_css_rules(css_text))
    findings = []
    for check in HOVER_CONTRAST_CHECKS:
        def is_dark_selector(selector: str) -> bool:
            return (
                'data-color-scheme="dark"' in selector
                or "data-color-scheme='dark'" in selector
                or ':not([data-color-scheme="light"])' in selector
                or ":not([data-color-scheme='light'])" in selector
            )

        matches = [
            (selector, declarations, lineno)
            for selector, declarations, lineno in rules
            if check["selector"] in selector
            and (is_dark_selector(selector) == (check["mode"] == "dark"))
        ]
        if not matches:
            findings.append({
                "file": str(path),
                "line": None,
                "severity": "ADVISORY",
                "rule": "known-hover-state-missing",
                "selector": check["selector"],
                "hover_state": check["name"],
                "detail": f"Required hover rule is missing: {check['selector']}.",
                "snippet": "",
            })
            continue

        # A selector can occur in more than one comma-separated rule.  Check
        # each declaration so a duplicate override cannot hide a bad value.
        for selector, declarations, lineno in matches:
            color_match = _HOVER_HEX_COLOR_RE.search(declarations)
            uses_accent_var = bool(_HOVER_VAR_COLOR_RE.search(declarations))
            if color_match:
                foreground = color_match.group(1)
            elif uses_accent_var:
                # The explicit AskJamie light rule is the only configured
                # variable-backed hover state.  Keep this fallback visible in
                # the report rather than treating an unresolved var as safe.
                foreground = "#2d6f7e" if check["mode"] == "light" else "#f07585"
            else:
                findings.append({
                    "file": str(path),
                    "line": lineno,
                    "severity": "ADVISORY",
                    "rule": "known-hover-state-unresolved",
                    "selector": selector,
                    "hover_state": check["name"],
                    "detail": (
                        f"Hover rule '{selector}' has no statically resolvable "
                        "text color declaration."
                    ),
                    "snippet": declarations.strip()[:120],
                })
                continue

            ratio = contrast_ratio(foreground, check["background"])
            if ratio >= 4.5:
                continue
            findings.append({
                "file": str(path),
                "line": lineno,
                "severity": "ADVISORY",
                "rule": "known-hover-state-contrast",
                "selector": selector,
                "hover_state": check["name"],
                "foreground": foreground,
                "background": check["background"],
                "contrast": round(ratio, 2),
                "passes_aa_normal": False,
                "detail": (
                    f"{check['name']} uses {foreground} on {check['background']} "
                    f"at {ratio:.2f}:1 — below WCAG AA normal-text minimum "
                    "(4.5:1)."
                ),
                "snippet": declarations.strip()[:120],
            })
    return findings


# ---------------------------------------------------------------------------
# Contrast helpers for findings
# ---------------------------------------------------------------------------

def _contrast_summary(is_var: bool) -> dict:
    """
    Return a dict with contrast ratios for the finding detail.

    is_var=True  → caller used var(--color-accent/rust); dark mode resolves
                   to the dark-mode accent token (#f07585 by default).
    is_var=False → caller hardcoded a light-mode hex; dark mode does NOT
                   override it, so contrast against dark surfaces improves
                   (dark bg is darker, making the warm accent stand out more).
    """
    light_ratio, light_hex = _worst_accent_light()

    if is_var:
        dark_ratio, dark_hex = _worst_accent_dark()
    else:
        # Hardcoded hex doesn't change in dark mode — pick the light accent
        # hex that has the worst light ratio (same hex stays in dark mode).
        light_ratio, light_hex = _worst_accent_light()
        dark_ratio = _worst_dark_contrast(light_hex)
        dark_hex = light_hex

    light_pass_normal = wcag_aa_normal(light_ratio)
    light_pass_large  = wcag_aa_large(light_ratio)
    dark_pass_normal  = wcag_aa_normal(dark_ratio)
    dark_pass_large   = wcag_aa_large(dark_ratio)

    return {
        "light_contrast":       round(light_ratio, 2),
        "light_accent_hex":     light_hex,
        "light_bg_hex":         LIGHT_MODE["bg"],
        "light_pass_aa_normal": light_pass_normal,
        "light_pass_aa_large":  light_pass_large,
        "dark_contrast":        round(dark_ratio, 2),
        "dark_accent_hex":      dark_hex if is_var else light_hex,
        "dark_bg_hex":          DARK_MODE["surface"],
        "dark_pass_aa_normal":  dark_pass_normal,
        "dark_pass_aa_large":   dark_pass_large,
    }


def _contrast_detail_suffix(cs: dict, is_bold_exempt: bool) -> str:
    """
    Build the human-readable contrast suffix included in every finding detail.

    Shows both light-mode and dark-mode contrast ratios and WCAG AA status.
    """
    lc = cs["light_contrast"]
    dc = cs["dark_contrast"]

    l_status = "✓ AA" if cs["light_pass_aa_normal"] else (
        "✓ AA large" if cs["light_pass_aa_large"] else "✗ below AA"
    )
    d_status = "✓ AA" if cs["dark_pass_aa_normal"] else (
        "✓ AA large" if cs["dark_pass_aa_large"] else "✗ below AA"
    )

    suffix = (
        f" Contrast — light: {lc:.2f}:1 ({l_status}), "
        f"dark: {dc:.2f}:1 ({d_status})."
    )
    return suffix


def _severity_from_contrast(cs: dict, is_bold_exempt: bool) -> str:
    """
    Compute severity given contrast summary and bold-exempt flag.

    ADVISORY — fails WCAG AA on normal text in *either* mode (and not exempt).
    INFO      — passes large/bold AA in both modes (or explicitly bold-exempt).
    """
    light_ok = cs["light_pass_aa_normal"] or (
        is_bold_exempt and cs["light_pass_aa_large"]
    )
    dark_ok  = cs["dark_pass_aa_normal"] or (
        is_bold_exempt and cs["dark_pass_aa_large"]
    )

    if light_ok and dark_ok:
        return "INFO"
    return "ADVISORY"


# ---------------------------------------------------------------------------
# CSS utilities
# ---------------------------------------------------------------------------

def _approx_px(value: float, unit: str) -> float:
    """Approximate pixel size from a CSS length at standard 16 px root."""
    unit = unit.lower()
    if unit in ("rem", "em"):
        return value * 16.0
    if unit == "px":
        return value
    if unit == "pt":
        return value * (4.0 / 3.0)
    return value * 16.0  # conservative fallback


def _block_qualifies_for_bold_exemption(declarations: str) -> bool:
    """
    Return True if this CSS rule block explicitly declares:
      - font-weight >= 600 / bold, AND
      - font-size that computes to >= 14 px (bold WCAG AA threshold)
    Both must be present in the same block — inherited values are not provable.
    """
    if not BOLD_WEIGHT_RE.search(declarations):
        return False
    fs_m = FONT_SIZE_RE.search(declarations)
    if not fs_m:
        return False  # no explicit size — cannot prove threshold is met
    approx = _approx_px(float(fs_m.group(1)), fs_m.group(2))
    return approx >= 14.0


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

def _inline_font_size_hint(line: str, tag: str, font_size_index: dict | None) -> str | None:
    """
    Return a font-size hint string for a Pass 1 HTML finding.

    Priority:
      1. An explicit font-size declared in the same inline style= attribute.
      2. The CSS inheritance estimate from *font_size_index* (if provided).
      3. None — caller may omit the hint from the finding.
    """
    # Check inline style= first (most specific)
    inline_fs_m = FONT_SIZE_RE.search(line)
    if inline_fs_m:
        approx = _approx_px(float(inline_fs_m.group(1)), inline_fs_m.group(2))
        return f"{inline_fs_m.group(1)}{inline_fs_m.group(2)} (~{approx:.0f}px, inline style)"

    if font_size_index is not None:
        return _resolve_inherited_font_size(tag, font_size_index)

    return None


def scan_html_file(path: Path, font_size_index: dict | None = None) -> list[dict]:
    """Return advisory findings for one HTML file (inline styles + utility classes).

    *font_size_index* — optional pre-built mapping from `build_font_size_index()`
    over the project CSS.  When provided, each finding's detail includes an
    estimated font size (explicit inline value or CSS inheritance heuristic),
    matching the hint already shown in Pass 2 (CSS rule) findings.
    """
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
                cs = _contrast_summary(is_var=False)
                severity = "ADVISORY" if tag in RISKY_TAGS else "INFO"
                font_size_hint = _inline_font_size_hint(line, tag, font_size_index)
                findings.append({
                    "file": str(path),
                    "line": lineno,
                    "severity": severity,
                    "tag": tag,
                    "rule": "inline-style-accent-color",
                    "font_size_hint": font_size_hint,
                    "detail": (
                        f"<{tag}> has inline accent color -- "
                        f"verify it is large/bold text (>=18.67 px normal "
                        f"or >=14 px bold)."
                        + (f" Font size: {font_size_hint}." if font_size_hint else "")
                        + _contrast_detail_suffix(cs, False)
                    ),
                    "snippet": stripped[:120],
                    **cs,
                })

        # 1b. Inline style= with accent var as text color
        if "style=" in line and ACCENT_VAR_PATTERN.search(line):
            if re.search(
                r"(?<!\w)color\s*:\s*var\(--color-(?:accent|rust)", line, re.IGNORECASE
            ):
                tag_m = re.search(r"<(\w+)\b", line)
                tag = tag_m.group(1).lower() if tag_m else "unknown"
                if tag in RISKY_TAGS:
                    cs = _contrast_summary(is_var=True)
                    font_size_hint = _inline_font_size_hint(line, tag, font_size_index)
                    findings.append({
                        "file": str(path),
                        "line": lineno,
                        "severity": "ADVISORY",
                        "tag": tag,
                        "rule": "inline-style-accent-var",
                        "font_size_hint": font_size_hint,
                        "detail": (
                            f"<{tag}> uses var(--color-accent/rust) as text color -- "
                            f"accent tokens are below 4.5:1 for normal body text."
                            + (f" Font size: {font_size_hint}." if font_size_hint else "")
                            + _contrast_detail_suffix(cs, False)
                        ),
                        "snippet": stripped[:120],
                        **cs,
                    })

        # 1c. Utility classes that apply accent color to text
        for cls in ACCENT_TEXT_CLASSES:
            if 'class="' in line and cls in line:
                tag_m = re.search(r"<(\w+)\b", line)
                tag = tag_m.group(1).lower() if tag_m else "unknown"
                if tag in RISKY_TAGS:
                    cs = _contrast_summary(is_var=True)
                    font_size_hint = _inline_font_size_hint(line, tag, font_size_index)
                    findings.append({
                        "file": str(path),
                        "line": lineno,
                        "severity": "ADVISORY",
                        "tag": tag,
                        "rule": f"utility-class-{cls}",
                        "font_size_hint": font_size_hint,
                        "detail": (
                            f"<{tag}> uses .{cls} -- verify it meets "
                            f"large/bold text threshold."
                            + (f" Font size: {font_size_hint}." if font_size_hint else "")
                            + _contrast_detail_suffix(cs, False)
                        ),
                        "snippet": stripped[:120],
                        **cs,
                    })

    return findings


# ---------------------------------------------------------------------------

def build_font_size_index(css_text: str) -> dict:
    """
    Build a mapping of final-element-type → list of
    (px_approx, raw_value, lineno, selector_part) for every CSS rule block
    in *css_text* that carries an explicit font-size declaration.

    Only static values (rem / em / px / pt) are recorded — clamp(), calc(),
    and percentage values are skipped because they can't be resolved statically.

    Rules are stored in source order so the caller can apply a scoring
    strategy rather than relying on order alone.
    """
    index: dict = {}
    for selector, declarations, lineno in extract_css_rules(css_text):
        fs_m = FONT_SIZE_RE.search(declarations)
        if not fs_m:
            continue
        approx = _approx_px(float(fs_m.group(1)), fs_m.group(2))
        raw = f"{fs_m.group(1)}{fs_m.group(2)}"
        for sel_part in selector.split(","):
            el = extract_final_element(sel_part.strip())
            if el:
                index.setdefault(el, []).append(
                    (approx, raw, lineno, sel_part.strip())
                )
    return index


def _resolve_inherited_font_size(selector: str, font_size_index: dict) -> str:
    """
    Best-effort estimate of the computed font-size for *selector* based on
    rules already collected in *font_size_index*.

    Strategy:
      1. Find all index entries for the same final element type.
      2. Score each candidate by counting how many simple tokens (classes,
         pseudo-classes, element names) from the candidate selector also appear
         in the flagged selector.  Higher score = closer ancestor or peer rule.
      3. Return the highest-scoring candidate or a UA-default estimate.

    This is a heuristic — not a full CSS cascade walk — but reliably surfaces
    the most likely inherited size for selectors nested inside the same scope
    (e.g. '.glee-main p' will prefer a '.glee-main p' font-size rule over an
    unrelated '.askjamie-main p' rule).
    """
    element = extract_final_element(selector)
    if element is None:
        return "inherited — check parent rules"

    candidates = font_size_index.get(element, [])

    if candidates:
        flagged_tokens = set(re.findall(r'[.#]?[a-zA-Z][a-zA-Z0-9_-]*', selector))

        def _score(cand):
            _, _, _, csel = cand
            cand_tokens = set(re.findall(r'[.#]?[a-zA-Z][a-zA-Z0-9_-]*', csel))
            return len(flagged_tokens & cand_tokens)

        best = max(candidates, key=_score)
        approx, raw, lineno, csel = best
        return f"~{approx:.0f}px (~{raw}, from '{csel[:55]}' at L{lineno})"

    # UA defaults for elements that differ from 16 px
    _UA_DEFAULTS: dict = {
        "small": 13.3, "sub": 12.0, "sup": 12.0,
    }
    ua_px = _UA_DEFAULTS.get(element, 16.0)
    return f"~{ua_px:.0f}px (browser default for <{element}>)"

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

    Dark-mode awareness (Task #69):
    - Each finding now carries light_contrast and dark_contrast ratios.
    - Severity is ADVISORY when the rule fails WCAG AA on *either* mode.
    - Rules using var(--color-accent) resolve to the dark-mode token in
      dark mode; hardcoded hex values do not change across modes.
    """
    try:
        css_text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    findings = []

    # Build font-size index for inheritance resolution (Pass 2 only)
    font_size_index = build_font_size_index(css_text)

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

        # Determine if usage is via CSS variable or hardcoded hex
        is_var = any(
            ACCENT_VAR_PATTERN.search(dl)
            for dl in decl_lines
            if not BG_BORDER_RE.search(dl) and not CSS_VAR_DEF_RE.match(dl)
        )

        # INFO exemption: same block must prove bold weight + explicit size >= 14 px
        qualifies_for_exemption = _block_qualifies_for_bold_exemption(declarations)

        # Font-size hint — explicit value in the same block takes precedence;
        # if absent, the per-selector inheritance resolver fills it in below.
        fs_m = FONT_SIZE_RE.search(declarations)
        if fs_m:
            fs_val = float(fs_m.group(1))
            fs_unit = fs_m.group(2)
            fs_approx = _approx_px(fs_val, fs_unit)
            rule_font_size_hint = f"{fs_m.group(1)}{fs_unit} (~{fs_approx:.0f}px, explicit in rule)"
        else:
            rule_font_size_hint = None  # resolved per selector part below

        cs = _contrast_summary(is_var=is_var)

        # Inspect each comma-separated selector part
        for sel_part in selector_raw.split(","):
            sel_part = sel_part.strip()
            if not sel_part:
                continue

            element = extract_final_element(sel_part)
            if element is None:
                continue  # class/id/attribute-only selector — skip

            if element in RISKY_TAGS:
                severity = _severity_from_contrast(cs, qualifies_for_exemption)

                # Per-selector font-size resolution
                font_size_hint = (
                    rule_font_size_hint
                    if rule_font_size_hint is not None
                    else _resolve_inherited_font_size(sel_part, font_size_index)
                )

                findings.append({
                    "file": str(path),
                    "line": lineno,
                    "severity": severity,
                    "selector": sel_part,
                    "tag": element,
                    "rule": "css-rule-accent-color",
                    "font_size_hint": font_size_hint,
                    "detail": (
                        f"CSS rule '{sel_part}' targets <{element}> with accent color"
                        + (
                            " (bold + explicit font-size >=14px in same block — INFO only)."
                            if qualifies_for_exemption
                            else " -- verify this element is always large/bold text "
                                 "(>=18.67 px normal or >=14 px bold)."
                        )
                        + f" Font size: {font_size_hint}."
                        + _contrast_detail_suffix(cs, qualifies_for_exemption)
                    ),
                    "snippet": f"{sel_part[:70]} {{ color: <accent>; }}",
                    **cs,
                })

    return findings




# ---------------------------------------------------------------------------
# Pass 3 — Hardcoded hex colors inside dark-mode CSS blocks
# ---------------------------------------------------------------------------

# Patterns that open a dark-mode scoped block:
#   @media (prefers-color-scheme: dark) { … }
#   html[data-color-scheme="dark"] .foo { … }   ← Glee-fully toggle
#   html[data-theme="dark"] .foo { … }          ← OKH JS toggle
_DARK_BLOCK_OPEN_RE = re.compile(
    r'(?:'
    r'@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)'
    r'|html\[data-color-scheme=["\'\']dark["\'\'][^{]*'
    r'|html\[data-theme=["\'\']dark["\'\'][^{]*'
    r')\s*\{',
    re.IGNORECASE,
)

# OKH dark-mode surface fallbacks — mirrors :root tokens in theme.css.
# Overridden at startup by parse_okh_root_tokens() so the scanner stays in
# sync with the CSS even when the root token values change.
# Source: :root { --color-bg: var(--okh-espresso)=#2a2320; --color-surface: #111827 }
_OKH_DARK_SURFACE_DEFAULTS = {
    "bg":      "#2a2320",  # --okh-espresso
    "surface": "#111827",  # --color-surface
}

# Live-parsed at import time; falls back to _OKH_DARK_SURFACE_DEFAULTS if the
# CSS file is absent or the tokens cannot be resolved.
_OKH_DARK_SURFACES = parse_okh_root_tokens(Path("assets/css/theme.css"))

# Matches a text `color:` with a hex value (not a CSS var or --def)
_DM_HEX_COLOR_RE = re.compile(
    r'(?<![a-z-])color\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b',
    re.IGNORECASE,
)


def _extract_dark_blocks(css_text):
    """Return list of (start_lineno, selector_context, block_content) for dark-mode blocks."""
    blocks = []
    for m in _DARK_BLOCK_OPEN_RE.finditer(css_text):
        selector_ctx = m.group(0).rstrip("{").strip()
        start_lineno = css_text[: m.start()].count("\n") + 1
        depth, i = 1, m.end()
        n = len(css_text)
        while i < n and depth > 0:
            if css_text[i] == "{":
                depth += 1
            elif css_text[i] == "}":
                depth -= 1
            i += 1
        blocks.append((start_lineno, selector_ctx, css_text[m.end() : i - 1]))
    return blocks


def scan_dark_mode_hex_colors(css_paths):
    """
    Pass 3 — scan every dark-mode CSS block in *css_paths* for hardcoded
    hex values used as text ``color:``.  Each hex is checked against the
    dark-mode surfaces in DARK_MODE.  A finding is emitted when the color
    fails WCAG AA normal text (< 4.5:1) against either dark surface.

    This catches cases where a developer writes e.g.:
        @media (prefers-color-scheme: dark) {
            .foo p { color: #8b2030; }   /* too dark on dark bg */
        }
    whose hex is not in ACCENT_HEX_PATTERN and would otherwise go undetected.
    """
    findings = []
    seen = set()  # (file, hex, lineno) dedup

    for css_path in css_paths:
        if not css_path.exists():
            continue
        try:
            css_text = css_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Strip block comments (preserve newlines so line numbers stay accurate)
        clean = re.sub(
            r"/\*.*?\*/",
            lambda m: "\n" * m.group(0).count("\n"),
            css_text,
            flags=re.DOTALL,
        )

        for block_start_line, selector_ctx, block_content in _extract_dark_blocks(clean):
            # Use OKH dark surfaces for html[data-theme="dark"] blocks;
            # use the Glee/prefers-color-scheme surfaces for all other dark blocks.
            if "data-theme" in selector_ctx:
                _dm_bg      = _OKH_DARK_SURFACES["bg"]
                _dm_surface = _OKH_DARK_SURFACES["surface"]
            else:
                _dm_bg      = DARK_MODE["bg"]
                _dm_surface = DARK_MODE["surface"]

            for ln_offset, raw_line in enumerate(block_content.splitlines()):
                stripped = raw_line.strip()
                if stripped.startswith("--"):
                    continue
                if re.search(r"(background|border)-color", stripped, re.IGNORECASE):
                    continue
                hex_m = _DM_HEX_COLOR_RE.search(stripped)
                if not hex_m:
                    continue

                hex_val = hex_m.group(1).lower()
                if len(hex_val) == 4:  # expand #abc -> #aabbcc
                    hex_val = "#" + "".join(c * 2 for c in hex_val[1:])

                lineno = block_start_line + ln_offset
                key = (str(css_path), hex_val, lineno)
                if key in seen:
                    continue
                seen.add(key)

                bg_ratio   = contrast_ratio(hex_val, _dm_bg)
                surf_ratio = contrast_ratio(hex_val, _dm_surface)
                worst_ratio = min(bg_ratio, surf_ratio)
                worst_bg = (
                    _dm_bg if bg_ratio <= surf_ratio else _dm_surface
                )

                passes_aa_normal = worst_ratio >= 4.5
                passes_aa_large  = worst_ratio >= 3.0

                if passes_aa_normal:
                    continue  # passes — no finding

                aa_status = (
                    "\u2717 AA normal, \u2713 AA large" if passes_aa_large
                    else "\u2717 below AA (all text sizes)"
                )

                findings.append({
                    "file": str(css_path),
                    "line": lineno,
                    "severity": "ADVISORY",
                    "rule": "dark-mode-hardcoded-hex-contrast",
                    "hex": hex_val,
                    "dark_bg_checked": worst_bg,
                    "dark_contrast": round(worst_ratio, 2),
                    "dark_pass_aa_normal": passes_aa_normal,
                    "dark_pass_aa_large":  passes_aa_large,
                    "detail": (
                        f"Hardcoded {hex_val} as text color inside dark-mode block "
                        f"(context: '{selector_ctx[:60]}\'). "
                        f"Contrast against dark surface {worst_bg}: "
                        f"{worst_ratio:.2f}:1 — {aa_status}. "
                        f"Fix: lighten the hex or switch to a CSS token that resolves "
                        f"to a passing value in dark mode."
                    ),
                    "snippet": stripped[:120],
                })

    return findings

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    strict = "--strict" in sys.argv

    # Parse live dark-mode tokens from theme.css before scanning
    global DARK_MODE
    theme_css = Path("assets/css/theme.css")
    DARK_MODE = parse_dark_mode_tokens(theme_css)

    root = Path(".")
    all_findings: list[dict] = []

    # Pre-build font-size index from all project CSS files so Pass 1 HTML findings
    # can include the same "~Npx" inheritance hint that Pass 2 CSS findings carry.
    _css_for_index = [
        p for p in sorted(root.rglob("*.css"))
        if not any(s in p.parts for s in SKIP_DIRS)
    ]
    _combined_css_text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in _css_for_index
        if p.exists()
    )
    _font_size_index = build_font_size_index(_combined_css_text)

    # Pass 1: HTML files
    html_scanned = 0
    for path in sorted(root.rglob("*.html")):
        if any(s in path.parts for s in SKIP_DIRS):
            continue
        all_findings.extend(scan_html_file(path, _font_size_index))
        html_scanned += 1

    # Pass 2: CSS files
    css_scanned = 0
    for css_path in CSS_FILES:
        if not css_path.exists():
            continue
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

    # Pass 3: hardcoded hex colors inside dark-mode CSS blocks
    all_css_paths = list(css_paths_seen) + [
        p for p in sorted(root.rglob("*.css"))
        if not any(s in p.parts for s in SKIP_DIRS)
        and p.resolve() not in css_paths_seen
    ]
    all_findings.extend(scan_dark_mode_hex_colors([Path(p) for p in all_css_paths]))

    # Pass 4: focused checks for the known hover states that have fixed
    # backgrounds in the Glee and AskJamie page skins.
    hover_findings = scan_hover_contrast(theme_css)
    all_findings.extend(hover_findings)

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
        "hover_check_count": len(HOVER_CONTRAST_CHECKS),
        "hover_failure_count": len(hover_findings),
        "findings": all_findings,
        "light_mode": {
            "bg": LIGHT_MODE["bg"],
            "surface": LIGHT_MODE["surface"],
            "accent_colors": LIGHT_MODE["accent_hex"],
            "worst_contrast": round(_worst_accent_light()[0], 2),
        },
        "dark_mode": {
            "bg": DARK_MODE["bg"],
            "surface": DARK_MODE["surface"],
            "accent_colors": DARK_MODE["accent_hex"],
            "worst_contrast": round(_worst_accent_dark()[0], 2),
            "source": str(theme_css) if theme_css.exists() else "defaults",
        },
        "rule": (
            "var(--color-accent) must not be used as the sole color signal for "
            "normal-weight body text smaller than 18.67 px. "
            "Light-mode contrast: #d94f63 = 3.37:1, #d35b2d = 3.55:1 (bg #f6f2ee). "
            "Dark-mode contrast: #f07585 = 4.9:1 (surface #241c1a). "
            "Passes WCAG 2.1 AA for large/bold text (>=18.67px normal or >=14px bold) "
            "but light-mode fails for normal body text. "
            "Any rule that fails on either mode is flagged ADVISORY."
        ),
        "passes": [
            "Pass 1 — HTML inline style= attributes and utility class names",
            "Pass 2 — CSS rule blocks in project stylesheet(s)",
            "Pass 3 — Hardcoded hex text colors inside dark-mode CSS blocks",
            "Pass 4 — Known Glee/AskJamie hover-state colors against their surfaces",
        ],
    }
    out_path = out_dir / "accent-contrast-report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Human-readable output
    print("Accent contrast advisory scan (light + dark mode + known hover states)")
    print(f"  HTML files scanned : {html_scanned}")
    print(f"  CSS files scanned  : {css_scanned}")
    print(f"  Advisories         : {len(advisories)}")
    print(f"  Info notes         : {len(infos)}")
    print(f"  Hover checks       : {len(HOVER_CONTRAST_CHECKS)} "
          f"({len(hover_findings)} failures)")
    print(f"  Report             : {out_path}")

    # Print mode palette summary
    lw, lh = _worst_accent_light()
    dw, dh = _worst_accent_dark()
    print(f"\n  Light-mode palette : accent {lh} / bg {LIGHT_MODE['bg']} → {lw:.2f}:1")
    print(f"  Dark-mode palette  : accent {dh} / surface {DARK_MODE['surface']} → {dw:.2f}:1")

    if advisories:
        print("\nAdvisories (accent color on body-text elements):")
        for f in advisories:
            loc = f.get("selector") or f.get("tag", "unknown")
            print(f"  [ADVISORY] {f['file']}:{f['line']} — {loc}")
            print(f"    Rule     : {f['rule']}")
            print(f"    Detail   : {f['detail']}")
            print(f"    Snippet  : {f['snippet']}")
            lc = f.get("light_contrast", "?")
            dc = f.get("dark_contrast", "?")
            print(f"    Ratios   : light {lc}:1 / dark {dc}:1")
            fsh = f.get("font_size_hint")
            if fsh:
                print(f"    Font size: {fsh}")
            print()
    else:
        print("\n  No body-text accent color violations found.")

    if infos:
        print("Info notes (context-dependent -- review manually):")
        for f in infos:
            loc = f.get("selector") or f.get("tag", "unknown")
            lc = f.get("light_contrast", "?")
            dc = f.get("dark_contrast", "?")
            print(f"  [INFO] {f['file']}:{f['line']} {loc} -- {f['rule']} "
                  f"(light {lc}:1 / dark {dc}:1)")

    print()
    if hover_findings:
        print("Hover-state contrast failures:")
        for f in hover_findings:
            print(f"  [ADVISORY] {f['file']}:{f.get('line') or '?'} — "
                  f"{f.get('hover_state', f.get('selector', 'unknown'))}")
            print(f"    Detail   : {f['detail']}")
            print(f"    Snippet  : {f['snippet']}")
        print()

    print("Advisories are reported without --strict.")
    print("Use --strict to exit 1 on any advisory or hover-state failure.")

    if strict and advisories:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
