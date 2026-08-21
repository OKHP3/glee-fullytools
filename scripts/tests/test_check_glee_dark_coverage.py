#!/usr/bin/env python3
"""
Regression tests for check-glee-dark-coverage.py
==================================================
Covers the key correctness properties:

1. A GLEE light-hex background with a matching dark override -> passes.
2. A GLEE light-hex background with NO dark override -> fails (exit 1).
3. A GLEE light-hex background inside a *responsive @media block* (not a dark
   block) with no dark override -> fails.  This is the line-offset regression:
   inner rules must use absolute line numbers so the GLEE section filter
   includes them.
4. Gradient backgrounds are excluded (decorative accent lines, not surfaces).
5. Comma-grouped selectors: ALL components must be covered, not just one.
6. Near-collision: selector '.foo' must not be considered covered by a dark rule
   for '.foo-extended' (endswith guard, no false blob-substring matches).
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Load the module under test (filename has hyphens -> can't use normal import)
# ---------------------------------------------------------------------------
_SCRIPT = Path(__file__).resolve().parent.parent / "check-glee-dark-coverage.py"
_spec = importlib.util.spec_from_file_location("_check_glee_dark_coverage", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Helper: build a minimal theme.css fixture string
# ---------------------------------------------------------------------------

# Section banners are plain CSS comments that satisfy the GLEE_START_RE and
# GLEE_END_RE patterns used by _glee_line_range().
_GLEE_BANNER = "/* SECTION \xb7 GLEE */\n"
_ASKJAMIE_BANNER = "/* SECTION \xb7 ASKJAMIE */\n"


_THIRD_SECTION_BANNER = "/* SECTION \xb7 COMPONENTS */\n"


def _make_css(*glee_body_parts: str) -> str:
    """Wrap body CSS lines in the GLEE + ASKJAMIE section banners."""
    return _GLEE_BANNER + "\n".join(glee_body_parts) + "\n" + _ASKJAMIE_BANNER


def _run_check(css: str) -> int:
    """Write css to a temp file, point mod.THEME_CSS at it, run mod.check()."""
    with tempfile.NamedTemporaryFile(
        suffix=".css", mode="w", encoding="utf-8", delete=False
    ) as fh:
        fh.write(css)
        tmp = Path(fh.name)
    orig = mod.THEME_CSS
    try:
        mod.THEME_CSS = tmp
        return mod.check(verbose=False)
    finally:
        mod.THEME_CSS = orig
        tmp.unlink(missing_ok=True)


def _run_check_section(
    css: str, section: str, require_both: bool = False
) -> int:
    """Run a named section fixture with optional strict two-form coverage."""
    with tempfile.NamedTemporaryFile(
        suffix=".css", mode="w", encoding="utf-8", delete=False
    ) as fh:
        fh.write(css)
        tmp = Path(fh.name)
    orig = mod.THEME_CSS
    try:
        mod.THEME_CSS = tmp
        return mod.check(
            verbose=False, require_both=require_both, section=section
        )
    finally:
        mod.THEME_CSS = orig
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_covered_rule_passes():
    """A light background with a matching dark override should pass (exit 0)."""
    css = _make_css(
        ".glee-main .widget { background: #fff7f1; }",
        'html[data-color-scheme="dark"] .glee-main .widget { background: #2a2724; }',
    )
    assert _run_check(css) == 0, "Expected exit 0 when dark override present"


def test_uncovered_rule_fails():
    """A light background with no dark override should fail (exit 1)."""
    css = _make_css(
        ".glee-main .widget { background: #fff7f1; }",
    )
    assert _run_check(css) == 1, "Expected exit 1 when dark override missing"


def test_nested_responsive_media_rule_is_caught():
    """
    A light background inside a non-dark responsive @media block in the GLEE
    section must be flagged when it has no dark override.

    Line-offset regression: before the fix the inner rule got start_line ~= 2
    (relative to the @media block content) and escaped the GLEE section filter.
    """
    css = _make_css(
        "@media (min-width: 768px) {",
        "  .glee-main .responsive-card { background: #ffe8a8; }",
        "}",
    )
    assert _run_check(css) == 1, (
        "Expected exit 1: light bg inside responsive @media must be detected"
    )


def test_nested_responsive_media_rule_with_dark_override_passes():
    """A responsive @media light bg that has a dark override should pass."""
    css = _make_css(
        "@media (min-width: 768px) {",
        "  .glee-main .responsive-card { background: #ffe8a8; }",
        "}",
        'html[data-color-scheme="dark"] .glee-main .responsive-card { background: #3a2f2a; }',
    )
    assert _run_check(css) == 0, (
        "Expected exit 0 when dark override covers responsive rule"
    )


def test_gradient_background_excluded():
    """Linear-gradient backgrounds (decorative accents) must not be flagged."""
    css = _make_css(
        ".glee-main .nav-line::after { "
        "background: linear-gradient(90deg, #d35b2d, #f3b932); }",
    )
    assert _run_check(css) == 0, "Expected exit 0: gradient is not a surface background"


def test_grouped_selector_all_must_be_covered():
    """
    Comma-grouped selector: ALL components must have dark overrides.
    Covering only one component while leaving the other uncovered -> exit 1.
    """
    css = _make_css(
        ".glee-main .alpha,",
        ".glee-main .beta { background: #fff7f1; }",
        # Only .alpha is covered
        'html[data-color-scheme="dark"] .glee-main .alpha { background: #2a2724; }',
    )
    assert _run_check(css) == 1, (
        "Expected exit 1: .beta is uncovered; any() would wrongly pass this"
    )


def test_grouped_selector_all_covered_passes():
    """All components of a comma-grouped selector covered -> exit 0."""
    css = _make_css(
        ".glee-main .alpha,",
        ".glee-main .beta { background: #fff7f1; }",
        'html[data-color-scheme="dark"] .glee-main .alpha { background: #2a2724; }',
        'html[data-color-scheme="dark"] .glee-main .beta { background: #2a2724; }',
    )
    assert _run_check(css) == 0, (
        "Expected exit 0 when all grouped selectors are covered"
    )


def test_no_false_positive_from_selector_prefix_collision():
    """
    '.foo' must not be considered covered by a dark rule for '.foo-extended'.
    Substring blob matching would produce a false positive; endswith must not.
    """
    css = _make_css(
        ".glee-main .foo { background: #fff7f1; }",
        # Dark rule covers .foo-extended, NOT .foo
        'html[data-color-scheme="dark"] .glee-main .foo-extended { background: #2a2724; }',
    )
    assert _run_check(css) == 1, (
        "Expected exit 1: '.foo' coverage by '.foo-extended' is a false positive"
    )


# ---------------------------------------------------------------------------
# AskJamie surface coverage
# ---------------------------------------------------------------------------

def test_askjamie_uncovered_surface_fails():
    """An AskJamie light background with no dark override should fail (exit 1)."""
    css = (
        _GLEE_BANNER
        + _ASKJAMIE_BANNER
        + ".askjamie-main .card { background: #fff7f1; }\n"
    )
    assert _run_check_section(css, section="askjamie") == 1, (
        "Expected exit 1: AskJamie light bg with no dark override must be flagged"
    )


def test_askjamie_covered_surface_passes():
    """An AskJamie light background with a dark override should pass (exit 0)."""
    css = (
        _GLEE_BANNER
        + _ASKJAMIE_BANNER
        + ".askjamie-main .card { background: #fff7f1; }\n"
        + 'html[data-color-scheme="dark"] .askjamie-main .card { background: #1e1c1a; }\n'
    )
    assert _run_check_section(css, section="askjamie") == 0, (
        "Expected exit 0: AskJamie light bg with dark override must pass"
    )


def test_askjamie_nested_responsive_media_rule_is_caught():
    """
    A light background inside a non-dark responsive @media block in the
    ASKJAMIE section must be flagged when it has no dark override.

    This guards against the parser's recursive line numbers escaping the
    AskJamie section filter, the same regression previously covered for GLEE.
    """
    css = (
        _GLEE_BANNER
        + _ASKJAMIE_BANNER
        + "@media (min-width: 768px) {\n"
        + "  .askjamie-main .responsive-card { background: #ffe8a8; }\n"
        + "}\n"
    )
    assert _run_check_section(css, section="askjamie") == 1, (
        "Expected exit 1: AskJamie light bg inside responsive @media must be detected"
    )


def test_askjamie_nested_responsive_media_rule_with_dark_override_passes():
    """An AskJamie responsive light bg with a dark override should pass."""
    css = (
        _GLEE_BANNER
        + _ASKJAMIE_BANNER
        + "@media (min-width: 768px) {\n"
        + "  .askjamie-main .responsive-card { background: #ffe8a8; }\n"
        + "}\n"
        + 'html[data-color-scheme="dark"] .askjamie-main .responsive-card { background: #3a2f2a; }\n'
    )
    assert _run_check_section(css, section="askjamie") == 0, (
        "Expected exit 0 when AskJamie responsive rule has a dark override"
    )


def test_askjamie_attr_only_fails_when_both_forms_required():
    """AskJamie attr-only coverage must fail with require_both enabled."""
    css = (
        _GLEE_BANNER
        + _ASKJAMIE_BANNER
        + ".askjamie-main .card { background: #fff7f1; }\n"
        + 'html[data-color-scheme="dark"] .askjamie-main .card { background: #1e1c1a; }\n'
    )
    assert _run_check_section(css, section="askjamie") == 0
    assert _run_check_section(css, section="askjamie", require_both=True) == 1


def test_askjamie_media_only_fails_when_both_forms_required():
    """AskJamie media-only coverage must fail with require_both enabled."""
    css = (
        _GLEE_BANNER
        + _ASKJAMIE_BANNER
        + ".askjamie-main .card { background: #fff7f1; }\n"
        + "@media (prefers-color-scheme: dark) {\n"
        + '  html:not([data-color-scheme="light"]) .askjamie-main .card { background: #1e1c1a; }\n'
        + "}\n"
    )
    assert _run_check_section(css, section="askjamie", require_both=True) == 1


def test_askjamie_both_forms_pass_when_both_forms_required():
    """AskJamie coverage in both forms must pass with require_both enabled."""
    css = (
        _GLEE_BANNER
        + _ASKJAMIE_BANNER
        + ".askjamie-main .card { background: #fff7f1; }\n"
        + 'html[data-color-scheme="dark"] .askjamie-main .card { background: #1e1c1a; }\n'
        + "@media (prefers-color-scheme: dark) {\n"
        + '  html:not([data-color-scheme="light"]) .askjamie-main .card { background: #1e1c1a; }\n'
        + "}\n"
    )
    assert _run_check_section(css, section="askjamie", require_both=True) == 0


def test_section_all_require_both_checks_askjamie():
    """The strict all-sections path must include AskJamie coverage."""
    css = (
        _GLEE_BANNER
        + ".glee-main .widget { background: #fff7f1; }\n"
        + 'html[data-color-scheme="dark"] .glee-main .widget { background: #2a2724; }\n'
        + "@media (prefers-color-scheme: dark) {\n"
        + '  html:not([data-color-scheme="light"]) .glee-main .widget { background: #2a2724; }\n'
        + "}\n"
        + _ASKJAMIE_BANNER
        + ".askjamie-main .card { background: #fff7f1; }\n"
        + 'html[data-color-scheme="dark"] .askjamie-main .card { background: #1e1c1a; }\n'
        + "@media (prefers-color-scheme: dark) {\n"
        + '  html:not([data-color-scheme="light"]) .askjamie-main .card { background: #1e1c1a; }\n'
        + "}\n"
    )
    assert _run_check_section(css, section="all", require_both=True) == 0


# ---------------------------------------------------------------------------
# --section all path
# ---------------------------------------------------------------------------

def test_section_all_passes_when_both_covered():
    """--section all should pass (exit 0) when both GLEE and AskJamie are covered."""
    css = (
        _GLEE_BANNER
        + ".glee-main .widget { background: #fff7f1; }\n"
        + 'html[data-color-scheme="dark"] .glee-main .widget { background: #2a2724; }\n'
        + _ASKJAMIE_BANNER
        + ".askjamie-main .card { background: #fff7f1; }\n"
        + 'html[data-color-scheme="dark"] .askjamie-main .card { background: #1e1c1a; }\n'
    )
    assert _run_check_section(css, section="all") == 0, (
        "Expected exit 0: both GLEE and AskJamie covered → all must pass"
    )


def test_section_all_fails_when_askjamie_uncovered():
    """--section all should fail (exit 1) when AskJamie has an uncovered rule."""
    css = (
        _GLEE_BANNER
        + ".glee-main .widget { background: #fff7f1; }\n"
        + 'html[data-color-scheme="dark"] .glee-main .widget { background: #2a2724; }\n'
        + _ASKJAMIE_BANNER
        + ".askjamie-main .card { background: #fff7f1; }\n"
    )
    assert _run_check_section(css, section="all") == 1, (
        "Expected exit 1: uncovered AskJamie rule must propagate through --section all"
    )


# ---------------------------------------------------------------------------
# Section-boundary detection when a later CSS section is present
# ---------------------------------------------------------------------------

def test_askjamie_boundary_stops_at_later_section():
    """
    When a third section banner follows ASKJAMIE, the ASKJAMIE check must not
    pick up rules from beyond that boundary.

    Regression guard: _section_line_range must treat the next SECTION banner
    as the end marker regardless of its name, so a rule placed after a
    COMPONENTS (or any third) banner is not counted as AskJamie.
    """
    css = (
        _GLEE_BANNER
        + _ASKJAMIE_BANNER
        # Covered AskJamie rule — inside the ASKJAMIE section.
        + ".askjamie-main .card { background: #fff7f1; }\n"
        + 'html[data-color-scheme="dark"] .askjamie-main .card { background: #1e1c1a; }\n'
        + _THIRD_SECTION_BANNER
        # Uncovered rule — outside the ASKJAMIE section; must not bleed in.
        + ".components-widget { background: #fff7f1; }\n"
    )
    assert _run_check_section(css, section="askjamie") == 0, (
        "Expected exit 0: rule after the COMPONENTS banner must not be "
        "counted as AskJamie; section boundary detection failed"
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _GREEN = "\033[32m"
    _RED   = "\033[31m"
    _RESET = "\033[0m"

    _tests = [
        test_covered_rule_passes,
        test_uncovered_rule_fails,
        test_nested_responsive_media_rule_is_caught,
        test_nested_responsive_media_rule_with_dark_override_passes,
        test_gradient_background_excluded,
        test_grouped_selector_all_must_be_covered,
        test_grouped_selector_all_covered_passes,
        test_no_false_positive_from_selector_prefix_collision,
        # AskJamie surface coverage
        test_askjamie_uncovered_surface_fails,
        test_askjamie_covered_surface_passes,
        test_askjamie_nested_responsive_media_rule_is_caught,
        test_askjamie_nested_responsive_media_rule_with_dark_override_passes,
        test_askjamie_attr_only_fails_when_both_forms_required,
        test_askjamie_media_only_fails_when_both_forms_required,
        test_askjamie_both_forms_pass_when_both_forms_required,
        test_section_all_require_both_checks_askjamie,
        # --section all path
        test_section_all_passes_when_both_covered,
        test_section_all_fails_when_askjamie_uncovered,
        # Section-boundary detection
        test_askjamie_boundary_stops_at_later_section,
    ]

    failures = 0
    for fn in _tests:
        try:
            fn()
            print(f"  {_GREEN}PASS{_RESET}  {fn.__name__}")
        except AssertionError as exc:
            print(f"  {_RED}FAIL{_RESET}  {fn.__name__}: {exc}")
            failures += 1
        except Exception as exc:
            import traceback
            print(f"  {_RED}ERR {_RESET}  {fn.__name__}: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            failures += 1

    print()
    if failures:
        print(f"{failures} test(s) FAILED")
        sys.exit(1)
    else:
        print(f"All {len(_tests)} tests passed.")
        sys.exit(0)
