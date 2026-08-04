#!/usr/bin/env python3
"""
check-glee-dark-coverage.py
===========================
Scans the GLEE section of assets/css/theme.css for CSS rules that use a
hardcoded light-hex value in any of the following surface-forming properties
and verifies that each such selector has a matching dark-mode override:

  background / background-color
  border / border-{side} / border-color / border-{side}-color
  outline / outline-color
  box-shadow

A "dark-mode override" means the same (normalised) selector appears inside
either:

  html[data-color-scheme="dark"] { … }
or
  @media (prefers-color-scheme: dark) { … }

…and that block also sets the *same property group* as the light-hex hit.
For example, a dark rule that only overrides ``background`` does NOT satisfy
coverage for a light-hex ``border-color`` hit on the same selector.

What counts as a "light-hex value"
-------------------------------------
Only *flat* hex values trigger this check:
    background: #fff7f1;          ← flagged
    border-color: #ffd8d2;        ← flagged
    background: linear-gradient(…, #f3b932, …);  ← skipped for background
                                                    (gradient decoration)

For ``background``/``background-color``, gradient values are skipped because
they are typically decorative accent lines and the light hex inside them
usually co-exists with a dark companion hex in the same gradient.
For border, outline, and shadow properties, gradients do not apply.

Exit codes
----------
  0 — all light-hex GLEE selectors have dark-mode overrides (or none found)
  1 — one or more selectors are uncovered

Usage
-----
  python3 scripts/check-glee-dark-coverage.py [--verbose]

  --verbose   Print each selector checked (pass or fail).

The check is also called by scripts/validate-site.py as part of the CI gate.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
THEME_CSS = ROOT / "assets" / "css" / "theme.css"

# Hex-color pattern whose first digit is 'e' or 'f' — the light end of the
# spectrum.  Matches 3-digit, 4-digit (alpha), 6-digit, and 8-digit forms.
LIGHT_HEX_RE = re.compile(r"#[eEfF][0-9a-fA-F]{2,7}\b")

# Background property: captures the full value up to ';' or end of line.
BACKGROUND_PROP_RE = re.compile(
    r"\bbackground(?:-color)?\s*:\s*(.+?)(?:\s*;|\s*$)",
    re.IGNORECASE,
)

# Gradient function — values that start with a CSS gradient keyword are
# decorative and are excluded from the surface-background check.
GRADIENT_RE = re.compile(
    r"^\s*(?:linear|radial|conic|repeating-linear|repeating-radial|repeating-conic)-gradient\s*\(",
    re.IGNORECASE,
)

# Border properties: border (shorthand), border-color, border-{side},
# border-{side}-color — but NOT border-radius / border-style / border-width /
# border-image / border-spacing / border-collapse.
BORDER_PROP_RE = re.compile(
    r"\bborder(?:-(?:top|right|bottom|left)(?:-color)?|-color)?\s*:\s*(.+?)(?:\s*;|\s*$)",
    re.IGNORECASE,
)

# Outline shorthand and outline-color (not outline-offset/style/width).
OUTLINE_PROP_RE = re.compile(
    r"\boutline(?:-color)?\s*:\s*(.+?)(?:\s*;|\s*$)",
    re.IGNORECASE,
)

# Box-shadow value.
BOX_SHADOW_PROP_RE = re.compile(
    r"\bbox-shadow\s*:\s*(.+?)(?:\s*;|\s*$)",
    re.IGNORECASE,
)

# All property groups checked for hardcoded light-hex values.
# Tuple: (label, regex, skip_gradients)
#   skip_gradients=True  → decorative gradient values are not flagged
#   skip_gradients=False → any light hex in the value is flagged
PROP_CHECKS: list[tuple[str, re.Pattern, bool]] = [
    ("background", BACKGROUND_PROP_RE, True),
    ("border",     BORDER_PROP_RE,     False),
    ("outline",    OUTLINE_PROP_RE,    False),
    ("shadow",     BOX_SHADOW_PROP_RE, False),
]

# Markers that delimit the GLEE section in the CSS comment banner
GLEE_START_RE = re.compile(r"SECTION\s*[·•]\s*GLEE", re.IGNORECASE)
GLEE_END_RE   = re.compile(r"SECTION\s*[·•]\s*ASKJAMIE", re.IGNORECASE)

# Dark-mode selector patterns (the outer wrapper selector / at-rule)
DARK_SELECTOR_RE = re.compile(r'data-color-scheme\s*=\s*"dark"')
DARK_MEDIA_RE    = re.compile(r"@media[^{]*prefers-color-scheme\s*:\s*dark")


def _ws_norm(text: str) -> str:
    """Collapse runs of whitespace (including newlines) to a single space."""
    return re.sub(r"\s+", " ", text).strip()


# Patterns to strip from dark-mode selectors when deriving their "base"
# equivalent, so the coverage check can compare against the light-mode
# selector regardless of how the dark-mode qualifier was attached.
#
# Three forms are normalised:
#   1. html[data-color-scheme="dark"]:has(…)   → html:has(…)
#   2. html[data-color-scheme="dark"] .foo      → .foo  (leading "html " removed)
#   3. html:not([data-color-scheme="light"]) …  → corresponding strip
_DARK_ATTR_RE = re.compile(r'\[data-color-scheme\s*=\s*"dark"\]')
_NOT_LIGHT_ATTR_RE = re.compile(r':not\(\s*\[data-color-scheme\s*=\s*"light"\]\s*\)')


def _strip_dark_qualifier(selector: str) -> str:
    """
    Remove dark-mode attribute qualifiers from a selector string so the
    remainder can be compared against the equivalent light-mode selector.

    Examples:
      'html[data-color-scheme="dark"] .glee-main .foo'
        → '.glee-main .foo'
      'html[data-color-scheme="dark"]:has(head > meta) body .foo'
        → 'html:has(head > meta) body .foo'
      'html:not([data-color-scheme="light"]) .glee-main .foo'
        → '.glee-main .foo'
    """
    s = _DARK_ATTR_RE.sub("", selector)
    s = _NOT_LIGHT_ATTR_RE.sub("", s)
    # If that leaves a bare 'html' with only whitespace before the next token,
    # and 'html' is now just an empty qualifier wrapper with nothing after
    # it (e.g. 'html .glee-main .foo'), keep 'html' — it is valid.
    # But if it left 'html ' with no pseudo/attribute, collapse:
    # 'html .foo' stays as-is (it's a descendant combinator); fine.
    return _ws_norm(s)


# ---------------------------------------------------------------------------
# CSS block parser
# ---------------------------------------------------------------------------

class CSSRule(NamedTuple):
    selector: str        # raw selector text
    declarations: str    # raw text inside { … }
    start_line: int      # 1-based line number of the opening brace
    in_dark_media: bool  # True when nested inside a dark @media block


def _parse_rules(css_text: str, _line_offset: int = 0) -> list[CSSRule]:
    """
    Lightweight CSS rule parser.

    Returns a flat list of CSSRule objects for every selector block and every
    inner block found inside @media rules.  Dark @media blocks are identified
    and their inner rules are tagged with ``in_dark_media=True``.

    ``_line_offset`` is used internally during recursion to keep all
    ``start_line`` values absolute (relative to the outermost CSS text) even
    when the parser recurses into @media block substrings.  Callers must never
    pass this argument — it is threaded automatically.

    Without the offset, a rule inside an @media block at file line 4500 would
    report start_line=2 (relative to the block substring) and silently escape
    the GLEE section filter (glee_start=4354).
    """
    rules: list[CSSRule] = []
    lines = css_text.splitlines(keepends=True)

    # Build a character-position → line-number lookup (1-based, relative to
    # this css_text substring).  Add _line_offset to get absolute file lines.
    cum_len = [0]
    for line in lines:
        cum_len.append(cum_len[-1] + len(line))

    def _pos_to_line(pos: int) -> int:
        """Return 1-based line number relative to this css_text substring."""
        lo, hi = 0, len(cum_len) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum_len[mid] <= pos < cum_len[mid + 1]:
                return mid + 1
            elif pos >= cum_len[mid + 1]:
                lo = mid + 1
            else:
                hi = mid
        return lo + 1

    n = len(css_text)
    i = 0

    def _skip_comment(pos: int) -> int:
        end = css_text.find("*/", pos + 2)
        return end + 2 if end != -1 else n

    def _find_block_end(pos: int) -> tuple[int, str]:
        depth = 1
        start = pos
        while pos < n and depth > 0:
            ch = css_text[pos]
            if ch == "/" and pos + 1 < n and css_text[pos + 1] == "*":
                pos = _skip_comment(pos)
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            pos += 1
        return pos, css_text[start : pos - 1]

    while i < n:
        ch = css_text[i]
        if ch in (" ", "\t", "\n", "\r"):
            i += 1
            continue
        if ch == "/" and i + 1 < n and css_text[i + 1] == "*":
            i = _skip_comment(i)
            continue

        selector_start = i
        while i < n and css_text[i] != "{" and css_text[i] != ";":
            if css_text[i] == "/" and i + 1 < n and css_text[i + 1] == "*":
                i = _skip_comment(i)
            else:
                i += 1

        if i >= n:
            break

        if css_text[i] == ";":
            i += 1
            continue

        raw_selector = css_text[selector_start:i].strip()
        open_brace_pos = i
        i += 1
        block_end, block_content = _find_block_end(i)
        i = block_end

        if raw_selector.lstrip().startswith("@media"):
            # The block_content substring starts at the same line as the
            # opening brace.  Inner rules report line numbers relative to
            # block_content; adding (abs_brace_line - 1) makes them absolute.
            abs_brace_line = _pos_to_line(open_brace_pos) + _line_offset
            inner_offset = abs_brace_line - 1
            if DARK_MEDIA_RE.search(raw_selector):
                for rule in _parse_rules(block_content, _line_offset=inner_offset):
                    rules.append(CSSRule(
                        selector=rule.selector,
                        declarations=rule.declarations,
                        start_line=rule.start_line,  # already absolute
                        in_dark_media=True,
                    ))
            else:
                rules.extend(_parse_rules(block_content, _line_offset=inner_offset))
            continue

        # Absolute line number = relative line + outer offset
        line_no = _pos_to_line(open_brace_pos) + _line_offset
        rules.append(CSSRule(
            selector=raw_selector,
            declarations=block_content,
            start_line=line_no,
            in_dark_media=False,
        ))

    return rules


# ---------------------------------------------------------------------------
# Section-range detection
# ---------------------------------------------------------------------------

def _glee_line_range(css_text: str) -> tuple[int, int]:
    """Return (start_line, end_line) for the GLEE section (1-based, inclusive)."""
    lines = css_text.splitlines()
    start = end = None
    for idx, line in enumerate(lines, start=1):
        if start is None and GLEE_START_RE.search(line):
            start = idx
        elif start is not None and GLEE_END_RE.search(line):
            end = idx - 1
            break
    if start is None:
        raise ValueError("Could not locate the GLEE section in theme.css")
    if end is None:
        end = len(lines)
    return start, end


# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------

def check(verbose: bool = False) -> int:
    """Run the check.  Returns 0 (pass) or 1 (fail)."""
    if not THEME_CSS.exists():
        print(f"ERROR: {THEME_CSS} not found", file=sys.stderr)
        return 1

    css_text = THEME_CSS.read_text(encoding="utf-8", errors="replace")

    try:
        glee_start, glee_end = _glee_line_range(css_text)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if verbose:
        print(f"GLEE section: lines {glee_start}–{glee_end}")

    all_rules = _parse_rules(css_text)

    # glee_light_rules: each entry is (rule, hits) where hits is a list of
    # (prop_type, bad_declaration_string) tuples.
    glee_light_rules: list[tuple[CSSRule, list[tuple[str, str]]]] = []

    # Per-property-type sets of dark-mode selector strings (both raw and
    # dark-qualifier-stripped forms), so coverage matching can verify that
    # the dark override addresses the *same* property group as the hit.
    dark_by_type: dict[str, set[str]] = {pt: set() for pt, _, _ in PROP_CHECKS}

    for rule in all_rules:
        in_glee = glee_start <= rule.start_line <= glee_end
        is_dark_rule = DARK_SELECTOR_RE.search(rule.selector) or rule.in_dark_media

        # Collect light-hex hits across all property groups
        hits: list[tuple[str, str]] = []
        for prop_type, prop_re, skip_gradients in PROP_CHECKS:
            for line in rule.declarations.splitlines():
                m = prop_re.search(line)
                if not m:
                    continue
                value = m.group(1).strip()
                if skip_gradients and GRADIENT_RE.match(value):
                    continue  # decorative gradient — skip
                if LIGHT_HEX_RE.search(value):
                    hits.append((prop_type, m.group(0).strip()))

        if in_glee and hits:
            glee_light_rules.append((rule, hits))

        # Dark-mode coverage: record which property groups this dark rule covers.
        if is_dark_rule:
            for prop_type, prop_re, _ in PROP_CHECKS:
                if prop_re.search(rule.declarations):
                    # Expand comma-grouped dark selectors into individual
                    # components and store both the raw normalised form and the
                    # stripped form (dark qualifier removed).
                    for raw_comp in rule.selector.split(","):
                        norm = _ws_norm(raw_comp)
                        if norm:
                            dark_by_type[prop_type].add(norm)
                            stripped = _strip_dark_qualifier(norm)
                            if stripped:
                                dark_by_type[prop_type].add(stripped)

    def _is_covered(comp: str, prop_type: str) -> bool:
        """Return True when *comp* is covered by a dark rule for *prop_type*.

        A dark selector covers a light one when:
        - The dark selector equals the light selector exactly (after the dark
          qualifier was already stripped into dark_by_type), OR
        - The dark selector ends with ' ' + comp, meaning the dark rule is a
          more-specific selector that appends the same component with an extra
          scoping prefix (e.g. 'html[data-color-scheme="dark"] .glee-main .foo'
          becomes '.glee-main .foo' after stripping, which ends with ' .foo' if
          the light rule is just '.foo').

        Using endswith instead of substring search prevents '.foo' from
        accidentally matching '.foo-extended' or other longer tokens.
        """
        suffix = " " + comp
        for dark in dark_by_type[prop_type]:
            if dark == comp or dark.endswith(suffix):
                return True
        return False

    uncovered: list[tuple[CSSRule, list[tuple[str, str]]]] = []
    for rule, hits in glee_light_rules:
        base_norm = _ws_norm(rule.selector)
        # Split comma-grouped selectors.  ALL components must be covered for
        # EACH property-type that has a hit.
        components = [_ws_norm(c) for c in base_norm.split(",") if c.strip()]

        missing_hits: list[tuple[str, str]] = []
        for prop_type, decl in hits:
            missing_comps = [c for c in components if not _is_covered(c, prop_type)]
            if missing_comps:
                missing_hits.append((prop_type, decl))

        if not missing_hits:
            if verbose:
                print(f"  PASS  line {rule.start_line:5d}  {base_norm!r}")
        else:
            uncovered.append((rule, missing_hits))
            if verbose:
                print(f"  FAIL  line {rule.start_line:5d}  {base_norm!r}")
                for pt, decl in missing_hits:
                    print(f"         [{pt}] missing dark override for: {decl}")

    if uncovered:
        print(
            f"\ncheck-glee-dark-coverage: {len(uncovered)} GLEE selector(s) have "
            f"hardcoded light surface value(s) with no dark-mode override:\n"
        )
        for rule, missing_hits in uncovered:
            base_norm = _ws_norm(rule.selector)
            print(f"  theme.css line {rule.start_line}: {base_norm!r}")
            for prop_type, decl in missing_hits:
                print(f"      [{prop_type}] {decl}")
        print(
            f"\n  Add a dark-mode override for each selector above inside a\n"
            f'  html[data-color-scheme="dark"] block or a\n'
            f"  @media (prefers-color-scheme: dark) block in the GLEE section.\n"
        )
        return 1

    # Tally hits across all property types for the summary line
    total_rules = len(glee_light_rules)
    type_counts: dict[str, int] = {}
    for _, hits in glee_light_rules:
        for prop_type, _ in hits:
            type_counts[prop_type] = type_counts.get(prop_type, 0) + 1
    breakdown = ", ".join(
        f"{count} {pt}" for pt, count in sorted(type_counts.items()) if count
    )
    summary = f"{total_rules} light-surface rule(s)"
    if breakdown:
        summary += f" ({breakdown})"
    print(f"check-glee-dark-coverage: OK — {summary} in the GLEE section all have dark-mode overrides.")
    return 0


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv
    sys.exit(check(verbose=verbose))
