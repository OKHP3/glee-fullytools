#!/usr/bin/env python3
"""
validate-site.py — Whole-site metadata + structural validator
==============================================================
Walks every HTML page (excluding curated skips) and checks:

  * DOCTYPE present
  * <html lang="…">
  * Non-empty <title>
  * Non-empty meta description
  * Canonical link (and not pointing to homepage unless intentional)
  * og:url matches canonical
  * robots meta present
  * theme-color = brand rust
  * Manifest link present
  * Favicon SVG link present
  * app.js wired in (search.js merged into app.js 2026-05-04)
  * Skip-to-content link present
  * <main id="main"> landmark present
  * JSON-LD blocks parse as valid JSON
  * Exactly one <h1>

Global invariant checks (outside per-page loop):
  * CSS-lines drift: <!-- STAT:CSS-LINES --> in showcase/index.html must be
    within ±50 lines of the actual assets/css/theme.css line count.
    Run scripts/sync-portfolio-stats.py to fix a drift failure.

Writes:
  assets/audit/validation-report-2026-05-03.json   (machine-readable detail)

Exit code:
  0 if no critical defects, 1 otherwise.

Usage:
    python3 scripts/validate-site.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"node_modules", ".local", ".git", "attached_assets", "assets", ".pythonlibs", ".cache", ".agents"}
SITE = "https://glee-fully.tools"

# Pages that intentionally point canonical to the homepage / are noindex.
HOMEPAGE_CANONICAL_OK = {"index.html", "404.html", "under-construction.html"}


def expected_canonical(rel: Path) -> str:
    parts = rel.parts
    if rel.name == "index.html":
        if len(parts) == 1:
            return f"{SITE}/"
        return f"{SITE}/{'/'.join(parts[:-1])}/"
    return f"{SITE}/{rel.as_posix()}"


def check_page(rel: Path, html: str) -> dict:
    issues = []
    warnings = []

    if "<!DOCTYPE html>" not in html and "<!doctype html>" not in html.lower():
        issues.append("missing DOCTYPE")
    if not re.search(r'<html[^>]*\slang="[^"]+"', html):
        issues.append("missing <html lang>")

    title = re.search(r"<title>([^<]+)</title>", html)
    if not title or not title.group(1).strip():
        issues.append("missing/empty <title>")

    desc = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
    if not desc or not desc.group(1).strip():
        issues.append("missing meta description")

    canon_m = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', html)
    if not canon_m:
        issues.append("missing canonical")
    else:
        canon = canon_m.group(1)
        if rel.as_posix() not in HOMEPAGE_CANONICAL_OK and canon == f"{SITE}/":
            issues.append(f"canonical points to homepage but file isn't homepage")
        expected = expected_canonical(rel)
        if rel.as_posix() not in HOMEPAGE_CANONICAL_OK and canon != expected:
            warnings.append(f"canonical {canon!r} != expected {expected!r}")

    og_url = re.search(r'<meta\s+property="og:url"\s+content="([^"]+)"', html)
    if og_url and canon_m and og_url.group(1) != canon_m.group(1):
        issues.append("og:url != canonical")

    if not re.search(r'<meta\s+name="robots"\s+content="', html):
        warnings.append("missing robots meta")

    theme = re.search(r'<meta\s+name="theme-color"\s+content="([^"]+)"', html)
    if not theme:
        issues.append("missing theme-color")
    elif theme.group(1).lower() != "#d35b2d":
        issues.append(f"theme-color {theme.group(1)!r} != brand #d35b2d")

    if "favicon.svg" not in html:
        issues.append("missing SVG favicon link")
    if "site.webmanifest" not in html:
        issues.append("missing manifest link")

    if "app.js" not in html:
        warnings.append("app.js not wired in")  # search.js merged into app.js 2026-05-04

    if 'class="skip-to-content"' not in html and 'skip-to-content' not in html:
        warnings.append("missing skip-to-content link")
    if not re.search(r'<main[^>]*\bid="main"', html):
        warnings.append("missing <main id=\"main\">")

    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
    if len(h1s) == 0:
        issues.append("no <h1>")
    elif len(h1s) > 1:
        warnings.append(f"{len(h1s)} <h1> elements (expect 1)")

    # JSON-LD parseability
    for i, m in enumerate(re.finditer(
            r'<script\s+type="application/ld\+json">\s*(.*?)\s*</script>',
            html, re.DOTALL)):
        try:
            json.loads(m.group(1))
        except json.JSONDecodeError as e:
            issues.append(f"JSON-LD block #{i + 1} not parseable: {e.msg}")

    # Mermaid referral invariant: any page that embeds a Mermaid diagram
    # MUST surface the paid-referral credit exactly once.
    has_mermaid = bool(re.search(r'class="mermaid"', html))
    referral_count = len(re.findall(r'class="mermaid-referral"', html))
    if has_mermaid and referral_count == 0:
        issues.append("page embeds a Mermaid diagram but has no .mermaid-referral credit")
    elif has_mermaid and referral_count > 1:
        warnings.append(f"page has {referral_count} .mermaid-referral blocks (expect 1)")
    elif not has_mermaid and referral_count > 0:
        warnings.append(".mermaid-referral present on a page with no Mermaid diagram")

    return {"issues": issues, "warnings": warnings}


def main() -> int:
    pages = []
    total_issues = 0
    total_warnings = 0
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if any(s in rel.parts for s in SKIP_DIRS):
            continue
        result = check_page(rel, path.read_text(encoding="utf-8", errors="replace"))
        result["path"] = rel.as_posix()
        pages.append(result)
        total_issues += len(result["issues"])
        total_warnings += len(result["warnings"])

    audit_dir = ROOT / "assets" / "audit"
    audit_dir.mkdir(exist_ok=True)
    out = audit_dir / "validation-report-2026-05-03.json"
    out.write_text(json.dumps({
        "scanned": len(pages),
        "total_issues": total_issues,
        "total_warnings": total_warnings,
        "pages": pages,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # Human-readable summary
    print(f"\nScanned {len(pages)} pages")
    print(f"  issues:   {total_issues}")
    print(f"  warnings: {total_warnings}")
    print(f"  detail:   {out.relative_to(ROOT)}")

    if total_issues:
        print("\nPages with issues:")
        for p in pages:
            if p["issues"]:
                print(f"  - {p['path']}")
                for i in p["issues"]:
                    print(f"      ! {i}")

    # ── Global invariant: CSS-lines drift ────────────────────────────────────
    # The showcase page displays the theme.css line count via a STAT marker.
    # Catch drift >±50 lines so stale numbers don't reach production.
    # To fix: run  python3 scripts/sync-portfolio-stats.py
    CSS_DRIFT_TOLERANCE = 50
    css_drift_issue = _check_css_lines_drift(CSS_DRIFT_TOLERANCE)
    if css_drift_issue:
        print(f"\nCSS-lines drift: {css_drift_issue}")
        print("  Fix: python3 scripts/sync-portfolio-stats.py")
        total_issues += 1

    return 1 if total_issues else 0


def _check_css_lines_drift(tolerance: int = 50) -> str:
    """Return an error string if STAT:CSS-LINES in showcase/index.html
    differs from the actual theme.css line count by more than *tolerance*.
    Returns empty string when the check passes or cannot run."""
    theme_css = ROOT / "assets" / "css" / "theme.css"
    showcase = ROOT / "showcase" / "index.html"
    if not theme_css.exists() or not showcase.exists():
        return ""

    actual = sum(1 for _ in theme_css.open(encoding="utf-8", errors="replace"))

    html = showcase.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<!--\s*STAT:CSS-LINES\s*-->([\d,]+)<!--\s*/STAT:CSS-LINES\s*-->", html)
    if not m:
        return "STAT:CSS-LINES marker not found in showcase/index.html"

    recorded = int(m.group(1).replace(",", ""))
    drift = abs(actual - recorded)
    if drift > tolerance:
        return (
            f"theme.css has {actual:,} lines but showcase shows {recorded:,} "
            f"(drift {drift:+d}, tolerance ±{tolerance})"
        )
    return ""


if __name__ == "__main__":
    sys.exit(main())
