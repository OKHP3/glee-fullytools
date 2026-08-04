#!/usr/bin/env python3
"""
check-glee-dark-coverage.py
===========================
Scans the GLEE section of assets/css/theme.css for CSS rules that set a
hardcoded light-hex background (any value whose first hex digit after # is
'f' or 'e', e.g. #fff7f1, #ffe8a8, #e8e0d8) and verifies that each such
selector has a matching dark-mode override inside either:

  html[data-color-scheme="dark"] { … }
or
  @media (prefers-color-scheme: dark) { … }

A "match" means the whitespace-normalised base selector string appears
verbatim inside a dark-mode selector that also sets a background or
background-color property.

What counts as a "light-hex background"
-----------------------------------------
Only *flat* hex values trigger this check:
    background: #fff7f1;          ← flagged
    background-color: #ffe8a8;    ← flagged
    background: linear-gradient(…, #f3b932, …);  ← skipped (gradient decoration)

Gradients are skipped because they are typically decorative accent lines
(e.g. a hover underline), not surface fill backgrounds, and the light hex
inside them usually co-exists with a dark companion hex in the same gradient.

Exit codes
----------
  0 — all light-bg GLEE selectors have a dark-mode override (or none found)
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

    glee_light_rules: list[tuple[CSSRule, list[str]]] = []  # (rule, bad_values)
    # Individual (non-comma-grouped) normalised dark selector strings that carry
    # a background override — stored in both raw and dark-qualifier-stripped forms
    # so coverage matching can use exact / endswith comparison without blob search.
    dark_individual: set[str] = set()

    for rule in all_rules:
        in_glee = glee_start <= rule.start_line <= glee_end

        # Collect light-hex background values (flat hex only, no gradients)
        bad_values: list[str] = []
        for line in rule.declarations.splitlines():
            bg_m = BACKGROUND_PROP_RE.search(line)
            if not bg_m:
                continue
            value = bg_m.group(1).strip()
            if GRADIENT_RE.match(value):
                continue  # decorative gradient — skip
            if LIGHT_HEX_RE.search(value):
                bad_values.append(bg_m.group(0).strip())

        # Dark-mode rule with any background override?
        is_dark_bg_rule = (
            (DARK_SELECTOR_RE.search(rule.selector) or rule.in_dark_media)
            and BACKGROUND_PROP_RE.search(rule.declarations)
        )

        if in_glee and bad_values:
            glee_light_rules.append((rule, bad_values))

        if is_dark_bg_rule:
            # Expand comma-grouped dark selectors into individual components and
            # store both the raw normalised form and the stripped form (dark
            # qualifier removed).  Expanding here means coverage matching later
            # can work with individual selectors rather than blobs.
            for raw_comp in rule.selector.split(","):
                norm = _ws_norm(raw_comp)
                if norm:
                    dark_individual.add(norm)
                    stripped = _strip_dark_qualifier(norm)
                    if stripped:
                        dark_individual.add(stripped)

    def _is_covered_by_dark(comp: str) -> bool:
        """Return True when *comp* is covered by some selector in dark_individual.

        A dark selector covers a light one when:
        - The dark selector equals the light selector exactly (after the dark
          qualifier was already stripped into dark_individual), OR
        - The dark selector ends with ' ' + comp, meaning the dark rule is a
          more-specific selector that appends the same component with an extra
          scoping prefix (e.g. 'html[data-color-scheme="dark"] .glee-main .foo'
          becomes '.glee-main .foo' after stripping, which ends with ' .foo' if
          the light rule is just '.foo').

        Using endswith instead of substring search prevents '.foo' from
        accidentally matching '.foo-extended' or other longer tokens.
        """
        suffix = " " + comp
        for dark in dark_individual:
            if dark == comp or dark.endswith(suffix):
                return True
        return False

    uncovered: list[tuple[CSSRule, list[str]]] = []
    for rule, bad_values in glee_light_rules:
        base_norm = _ws_norm(rule.selector)
        # Split comma-grouped selectors.  ALL components must be covered —
        # if the rule is '.a, .b { background: #fff; }' then both .a and .b
        # carry the light background and both need a dark-mode override.
        components = [_ws_norm(c) for c in base_norm.split(",") if c.strip()]
        missing = [comp for comp in components if not _is_covered_by_dark(comp)]
        if not missing:
            if verbose:
                print(f"  PASS  line {rule.start_line:5d}  {base_norm!r}")
        else:
            uncovered.append((rule, bad_values))
            if verbose:
                detail = " | ".join(missing)
                print(f"  FAIL  line {rule.start_line:5d}  {base_norm!r}")
                if len(missing) < len(components):
                    # Some components are covered — flag which are missing
                    print(f"         missing dark override for: {detail}")

    if uncovered:
        print(
            f"\ncheck-glee-dark-coverage: {len(uncovered)} GLEE selector(s) have "
            f"a hardcoded light background with no dark-mode override:\n"
        )
        for rule, bad_values in uncovered:
            base_norm = _ws_norm(rule.selector)
            print(f"  theme.css line {rule.start_line}: {base_norm!r}")
            for v in bad_values:
                print(f"      {v}")
        print(
            f"\n  Add a dark-mode override for each selector above inside a\n"
            f'  html[data-color-scheme="dark"] block or a\n'
            f"  @media (prefers-color-scheme: dark) block in the GLEE section.\n"
        )
        return 1

    total = len(glee_light_rules)
    print(
        f"check-glee-dark-coverage: OK — {total} light-background rule(s) in the "
        f"GLEE section all have dark-mode overrides."
    )
    return 0


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv
    sys.exit(check(verbose=verbose))
