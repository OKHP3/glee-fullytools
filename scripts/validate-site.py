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

# Pages that intentionally omit the sparkle banner element.
# These are utility/error pages that have no site-specials section.
SPARKLE_EXEMPT = {"404.html", "under-construction.html"}

# Pages that intentionally omit the anti-FOSC color-scheme init script.
# The 404 and under-construction pages are standalone utility pages that
# have no color-scheme toggle, so the init script is not needed there.
COLOR_SCHEME_INIT_EXEMPT = {"404.html", "under-construction.html"}

# The idempotency marker written by scripts/inject-color-scheme-init.py.
# Its presence confirms the blocking inline script is in <head>.
COLOR_SCHEME_INIT_MARKER = "<!-- AUTOGEN:COLOR-SCHEME-INIT -->"


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

    # JSON-LD parseability + @graph structure
    for i, m in enumerate(re.finditer(
            r'<script\s+type="application/ld\+json">\s*(.*?)\s*</script>',
            html, re.DOTALL)):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            issues.append(f"JSON-LD block #{i + 1} not parseable: {e.msg}")
            continue
        g_issues, g_warnings = validate_jsonld_graph(data, block=i + 1)
        issues.extend(g_issues)
        warnings.extend(g_warnings)

    # Sparkle banner presence: every published page must carry the
    # <a data-sparkle-link> element so the no-JS fallback is always present.
    # Run scripts/sync-sparkle-fallback.py to add the element to new pages.
    if "data-sparkle-link" not in html and rel.name not in SPARKLE_EXEMPT:
        issues.append("missing data-sparkle-link element (run sync-sparkle-fallback.py)")

    # Anti-FOSC color-scheme init script: every Glee page must have the
    # blocking inline script injected by inject-color-scheme-init.py so users
    # who have pinned dark mode don't see a flash of the wrong theme on load.
    # Run scripts/inject-color-scheme-init.py to add it to new pages.
    if COLOR_SCHEME_INIT_MARKER not in html and rel.name not in COLOR_SCHEME_INIT_EXEMPT:
        warnings.append(
            "missing AUTOGEN:COLOR-SCHEME-INIT marker "
            "(run scripts/inject-color-scheme-init.py)"
        )

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

def validate_jsonld_graph(data: dict, block: int = 1) -> tuple[list, list]:
    """Validate the internal @graph structure of a parsed JSON-LD block.

    Checks:
      1. All @id cross-references within the graph resolve to an actual node.
      2. SoftwareApplication nodes have name, operatingSystem, applicationCategory,
         and at least one of offers / aggregateRating.
      3. BreadcrumbList is a top-level graph node (not nested inside another node)
         and has at least 2 itemListElement entries.

    Returns (issues, warnings) lists.
    """
    issues: list = []
    warnings: list = []

    graph = data.get("@graph")
    if not isinstance(graph, list):
        return issues, warnings  # no @graph -- nothing to validate here

    prefix = f"JSON-LD block #{block} @graph"

    # Build a set of @id values that exist as top-level graph nodes
    top_level_ids: set = set()
    for node in graph:
        if isinstance(node, dict) and "@id" in node:
            top_level_ids.add(node["@id"])

    # Helper: recursively collect all {"@id": ...} reference objects
    # (objects whose ONLY key is @id -- i.e. they are references, not nodes)
    def collect_id_refs(obj, inside_node_id=None):
        refs = []
        if isinstance(obj, dict):
            keys = set(obj.keys())
            if keys == {"@id"} and inside_node_id is not None:
                refs.append(obj["@id"])
            else:
                node_id = obj.get("@id", inside_node_id)
                for v in obj.values():
                    refs.extend(collect_id_refs(v, node_id))
        elif isinstance(obj, list):
            for item in obj:
                refs.extend(collect_id_refs(item, inside_node_id))
        return refs

    # Check 1: @id cross-references resolve
    for node in graph:
        for ref_id in collect_id_refs(node):
            if ref_id not in top_level_ids:
                issues.append(
                    f"{prefix}: @id reference {ref_id!r} does not resolve "
                    f"to any top-level graph node"
                )

    # Check 2: SoftwareApplication required fields
    SA_REQUIRED = ("name", "operatingSystem", "applicationCategory")
    for node in graph:
        if not isinstance(node, dict):
            continue
        node_type = node.get("@type", "")
        if node_type != "SoftwareApplication":
            continue
        node_id = node.get("@id", "(no @id)")
        for field in SA_REQUIRED:
            if not node.get(field):
                issues.append(
                    f"{prefix}: SoftwareApplication {node_id!r} missing required field {field!r}"
                )
        if not node.get("offers") and not node.get("aggregateRating"):
            issues.append(
                f"{prefix}: SoftwareApplication {node_id!r} must have "
                f"at least one of 'offers' or 'aggregateRating'"
            )

    # Check 3: BreadcrumbList is a top-level node and has >= 2 items
    def find_nested_breadcrumbs(obj, depth=0):
        """Recursively find BreadcrumbList nodes that are NOT top-level."""
        nested = []
        if isinstance(obj, dict):
            if depth > 0 and obj.get("@type") == "BreadcrumbList":
                nested.append(obj)
            for v in obj.values():
                nested.extend(find_nested_breadcrumbs(v, depth + 1))
        elif isinstance(obj, list):
            for item in obj:
                nested.extend(find_nested_breadcrumbs(item, depth))
        return nested

    for node in graph:
        if not isinstance(node, dict):
            continue
        # Check for nested BreadcrumbList inside this top-level node
        nested = find_nested_breadcrumbs(node, depth=0)
        for nb in nested:
            nb_id = nb.get("@id", "(no @id)")
            issues.append(
                f"{prefix}: BreadcrumbList {nb_id!r} is nested inside a node "
                f"instead of being a top-level graph entry"
            )
        # Validate top-level BreadcrumbList item count
        if node.get("@type") == "BreadcrumbList":
            node_id = node.get("@id", "(no @id)")
            items = node.get("itemListElement")
            if not isinstance(items, list) or len(items) < 2:
                count = len(items) if isinstance(items, list) else 0
                issues.append(
                    f"{prefix}: BreadcrumbList {node_id!r} has {count} itemListElement "
                    f"(need at least 2)"
                )

    return issues, warnings
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

    # ── Global invariant: showcase STAT markers (pages / tool-ettes / etc.) ─
    # showcase/index.html embeds live counts via <!-- STAT:X --> markers.
    # Catch drift > ±2 so a new page added without re-running sync is caught
    # before the showcase shows a stale number.
    # To fix: run  python3 scripts/sync-portfolio-stats.py
    stat_drift_issues = _check_stat_markers_drift(tolerance=2)
    for msg in stat_drift_issues:
        print(f"\nSTAT marker drift: {msg}")
    if stat_drift_issues:
        print("  Fix: python3 scripts/sync-portfolio-stats.py")
        total_issues += len(stat_drift_issues)

    # ── Global invariant: docs/adr/ index sync ────────────────────────────
    # Every *.md file in docs/adr/ (except README.md and template.md) must be
    # linked in the README index table. Catch a newly added ADR file that was
    # never registered, or a stale index row pointing to a deleted file.
    adr_drift_issue = _check_adr_index_sync()
    if adr_drift_issue:
        print(f"\nADR index drift: {adr_drift_issue}")
        print("  Fix: update docs/adr/README.md index table and AGENTS.md section 2.2.1")
        total_warnings += 1

    # ── Global invariant: scripts/*.py count vs AGENTS.md classification table ─
    # When a new .py script is added to scripts/ it must be classified in the
    # AGENTS.md script-categories table.  This check catches the drift so the
    # table stays accurate without a manual audit.
    # To fix: classify the script in AGENTS.md and bump <!-- STAT:SCRIPTS-PY -->.
    scripts_drift = _check_scripts_py_drift()
    if scripts_drift:
        print(f"\nscripts/ count drift: {scripts_drift}")
        print("  Fix: classify the script in AGENTS.md and bump <!-- STAT:SCRIPTS-PY -->")
        total_issues += 1

    # ── Global invariant: scripts/*.mjs + *.sh count vs AGENTS.md ────────────
    # When a new non-Python runner is added to scripts/ it must be classified
    # in the AGENTS.md script-categories table.  This check catches the drift.
    # To fix: classify the script in AGENTS.md and bump <!-- STAT:SCRIPTS-OTHER -->.
    scripts_non_py_drift = _check_scripts_non_py_drift()
    if scripts_non_py_drift:
        print(f"\nscripts/ non-Python count drift: {scripts_non_py_drift}")
        print("  Fix: classify the script in AGENTS.md and bump <!-- STAT:SCRIPTS-OTHER -->")
        total_issues += 1

    # ── Global invariant: og:image:alt / twitter:image:alt vs SVG aria-label ─
    # For every tool page whose og:image is a local .svg, the alt text must be
    # "Glee-fully {tool_name} — {svg[aria-label]}".  If an SVG's aria-label
    # changes the HTML meta tags won't update automatically — catch it here.
    # To fix: run  python3 scripts/sync-image-alt.py
    import html as _html_mod
    alt_mismatches = _check_og_image_alt_drift(_html_mod)
    for msg in alt_mismatches:
        print(f"\nog:image:alt drift: {msg}")
    if alt_mismatches:
        print("  Fix: python3 scripts/sync-image-alt.py")
        total_issues += len(alt_mismatches)

    # ── Global invariant: sparkle fallback sync ───────────────────────────────
    # Every HTML page carries a static <a data-sparkle-link> fallback built from
    # assets/data/sparkle.json.  If sparkle.json is edited without running
    # scripts/sync-sparkle-fallback.py the static markup silently goes stale.
    # To fix: run  python3 scripts/sync-sparkle-fallback.py
    sparkle_mismatches = _check_sparkle_drift()
    for msg in sparkle_mismatches:
        print(f"\nSparkle drift: {msg}")
    if sparkle_mismatches:
        print("  Fix: python3 scripts/sync-sparkle-fallback.py")
        total_issues += len(sparkle_mismatches)

    # ── Global invariant: Glee dark-mode coverage ─────────────────────────────
    # Every hardcoded light-hex background in the GLEE section of theme.css must
    # have a matching dark-mode override.  New rules added without a dark pair
    # silently break dark mode.
    # To fix: add a dark-mode override in a html[data-color-scheme="dark"] or
    #         @media (prefers-color-scheme: dark) block in the GLEE section.
    glee_dark_issues = _check_glee_dark_coverage()
    for msg in glee_dark_issues:
        print(f"\nGlee dark-mode coverage: {msg}")
    if glee_dark_issues:
        print(
            '  Fix: add html[data-color-scheme="dark"] or '
            "@media (prefers-color-scheme: dark) override in the GLEE section"
        )
        total_issues += len(glee_dark_issues)

    # ── Global invariant: CSS cache-buster token drift ────────────────────────
    # Every HTML page must reference theme.css with the current SHA-256 token so
    # browsers never serve a stale stylesheet after theme.css is updated.
    # To fix: run  python3 scripts/sync-css-version.py
    import hashlib as _hashlib
    css_token_issues = _check_css_token_drift(_hashlib)
    for msg in css_token_issues:
        print(f"\nCSS token drift: {msg}")
    if css_token_issues:
        print("  Fix: python3 scripts/sync-css-version.py")
        total_issues += len(css_token_issues)

    return 1 if total_issues else 0


def _check_stat_markers_drift(tolerance: int = 2) -> list:
    """Return a list of drift descriptions for STAT:PAGES, STAT:TOOL-ETTES,
    STAT:BRANCHES, and STAT:GPTS in showcase/index.html and about/index.html
    vs live counts derived from assets/data/search-index.json and the toolbox
    HTML files.

    Both files are patched by scripts/sync-portfolio-stats.py; both are checked
    here so drift is caught regardless of which page was manually edited.
    showcase/index.html is expected to carry all four markers — a missing marker
    there is reported as an error.  about/index.html may only contain a subset
    of markers (PAGES and GPTS today); absent markers are skipped silently and
    only present-but-drifted markers are reported.

    Uses the same counting logic as scripts/sync-portfolio-stats.py so the
    validator and the sync script stay in lockstep.

    Returns an empty list when all present markers are within *tolerance*."""
    index_json = ROOT / "assets" / "data" / "search-index.json"
    if not index_json.exists():
        return []

    # ── Compute live stats (mirrors sync-portfolio-stats.compute_stats()) ──
    idx = json.loads(index_json.read_text(encoding="utf-8"))
    pages_list = idx.get("pages", [])

    real = [
        p for p in pages_list
        if "/assets/" not in p["url"]
        and p["url"] not in ("/404/", "/under-construction/")
    ]

    tool_ette_pat = re.compile(r"^.*/toolbox/\d+-[^/]+/\d+[a-z]-[^/]+/$")
    branch_pat    = re.compile(r"^.*/toolbox/\d+-[^/]+/$")

    tool_ettes = [p for p in real if tool_ette_pat.match(p["url"])]
    branches   = [p for p in real if branch_pat.match(p["url"])]

    gpt_count = 0
    for f in sorted(ROOT.glob("toolbox/*/*/index.html")):
        html_text = f.read_text(encoding="utf-8", errors="replace")
        if re.search(r"chatgpt\.com|chat\.openai\.com", html_text):
            gpt_count += 1

    live = {
        "PAGES":      len(real),
        "TOOL-ETTES": len(tool_ettes),
        "BRANCHES":   len(branches),
        "GPTS":       gpt_count,
    }

    mismatches: list = []

    # Pages to check: (path, report_if_marker_absent)
    # showcase must carry all four markers; about may omit some by design.
    pages_to_check = [
        (ROOT / "showcase" / "index.html", True),
        (ROOT / "about"    / "index.html", False),
    ]

    for page_path, require_all_markers in pages_to_check:
        if not page_path.exists():
            continue
        page_label = page_path.relative_to(ROOT).as_posix()
        html = page_path.read_text(encoding="utf-8", errors="replace")

        for key, live_val in live.items():
            pattern = re.compile(
                r"<!-- STAT:" + re.escape(key) + r" -->([\d,]+)<!-- /STAT:" + re.escape(key) + r" -->"
            )
            # Use first occurrence (marker may appear multiple times; all should agree)
            m = pattern.search(html)
            if not m:
                if require_all_markers:
                    mismatches.append(f"STAT:{key} marker not found in {page_label}")
                continue  # absent marker in about is expected — skip silently
            recorded = int(m.group(1).replace(",", ""))
            drift = abs(live_val - recorded)
            if drift > tolerance:
                mismatches.append(
                    f"STAT:{key}: {page_label} shows {recorded} but live count is {live_val} "
                    f"(drift {live_val - recorded:+d}, tolerance ±{tolerance})"
                )

    return mismatches


def _check_og_image_alt_drift(html_mod) -> list:
    """Return a list of mismatch descriptions for pages with missing or mismatched
    og:image:alt / twitter:image:alt tags.

    Two tiers of checks:

    SVG og:image (tool pages):
      The alt text must match the formula 'Glee-fully {tool} — {svg[aria-label]}'.
      Both presence AND value are verified.

    Non-SVG og:image (homepage, about, contact, legal, etc.):
      Presence-only check — both og:image:alt and twitter:image:alt must exist.
      The actual text is not constrained (it is page-specific prose, not formula-derived).

    Returns an empty list when everything is in sync."""
    import html as _html_mod  # noqa: F811 — already imported by caller; harmless re-import
    mismatches: list = []
    site_prefix = "https://glee-fully.tools/"

    _ALT_CHECKS = (
        ("og:image:alt",      r'<meta\s+property="og:image:alt"\s+content="([^"]+)"'),
        ("twitter:image:alt", r'<meta\s+name="twitter:image:alt"\s+content="([^"]+)"'),
    )

    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if any(s in rel.parts for s in SKIP_DIRS):
            continue
        html_text = path.read_text(encoding="utf-8", errors="replace")

        # Require an og:image pointing to this site (any format)
        img_m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html_text)
        if not img_m:
            continue
        img_url = img_m.group(1)
        if not img_url.startswith(site_prefix):
            continue

        is_svg = img_url.lower().endswith(".svg")

        if is_svg:
            # ── SVG pages: presence + value check ──────────────────────────
            svg_rel = img_url[len(site_prefix):]
            svg_path = ROOT / svg_rel
            if not svg_path.exists():
                mismatches.append(f"{rel}: SVG not found at {svg_rel}")
                continue

            svg_text = svg_path.read_text(encoding="utf-8", errors="replace")
            aria_m = re.search(r'<svg\b[^>]*\baria-label="([^"]+)"', svg_text)
            if not aria_m:
                mismatches.append(f"{rel}: SVG {svg_rel} has no aria-label")
                continue
            aria_label = aria_m.group(1)

            title_m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html_text)
            if not title_m:
                mismatches.append(f"{rel}: no og:title to derive tool name")
                continue
            raw_title = _html_mod.unescape(title_m.group(1))
            for sep in (" \u2014 ", " - "):
                idx = raw_title.find(sep)
                if idx != -1:
                    tool_name = raw_title[:idx].strip()
                    break
            else:
                tool_name = raw_title.strip()

            expected = f"Glee-fully {tool_name} \u2014 {aria_label}"

            for prop, pattern in _ALT_CHECKS:
                alt_m = re.search(pattern, html_text)
                if not alt_m:
                    mismatches.append(
                        f"{rel}: missing {prop} (page has a .svg og:image but no alt tag)\n"
                        f"    expected: {expected!r}"
                    )
                    continue
                actual = _html_mod.unescape(alt_m.group(1))
                if actual != expected:
                    mismatches.append(
                        f"{rel} [{prop}]\n"
                        f"    expected: {expected!r}\n"
                        f"    actual:   {actual!r}"
                    )

        else:
            # ── Non-SVG pages: presence-only check ─────────────────────────
            # Text is page-specific prose; only absence is flagged.
            for prop, pattern in _ALT_CHECKS:
                if not re.search(pattern, html_text):
                    mismatches.append(
                        f"{rel}: missing {prop} "
                        f"(page has a non-SVG og:image but no alt tag)"
                    )

    return mismatches


def _check_adr_index_sync() -> str:
    """Return an error string when docs/adr/ files and the README index diverge.
    Returns empty string when in sync or the directory does not exist."""
    adr_dir = ROOT / "docs" / "adr"
    readme = adr_dir / "README.md"
    if not adr_dir.is_dir() or not readme.exists():
        return ""

    # ADR files are numbered *.md files -- exclude README.md and template.md
    adr_files = {
        p.name for p in adr_dir.glob("*.md")
        if p.name not in ("README.md", "template.md")
    }

    # Links in the index table look like: [NNNN](NNNN-title.md)
    readme_text = readme.read_text(encoding="utf-8", errors="replace")
    linked = set(re.findall(r'\]\((\d{4}-[^)]+\.md)\)', readme_text))

    unlinked = adr_files - linked
    dangling = linked - adr_files

    parts = []
    if unlinked:
        parts.append(f"files not in index: {', '.join(sorted(unlinked))}")
    if dangling:
        parts.append(f"index rows with no file: {', '.join(sorted(dangling))}")
    return "; ".join(parts)


def _check_scripts_py_drift() -> str:
    """Return an error string when the scripts/*.py count on disk does not match
    the <!-- STAT:SCRIPTS-PY --> marker in AGENTS.md.

    A mismatch means a new script was added (or removed) without updating the
    classification table, prompting the maintainer to classify it.
    Returns empty string when counts agree or the marker is absent."""
    agents_md = ROOT / "AGENTS.md"
    scripts_dir = ROOT / "scripts"
    if not agents_md.exists() or not scripts_dir.is_dir():
        return ""

    live_count = len(list(scripts_dir.glob("*.py")))
    agents_text = agents_md.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<!-- STAT:SCRIPTS-PY -->(\d+)<!-- /STAT:SCRIPTS-PY -->", agents_text)
    if not m:
        return "STAT:SCRIPTS-PY marker not found in AGENTS.md"
    recorded = int(m.group(1))
    if live_count != recorded:
        return (
            f"scripts/*.py count is {live_count} but AGENTS.md documents {recorded} "
            f"(drift {live_count - recorded:+d}). "
            f"Classify the new/removed script in AGENTS.md and bump the STAT:SCRIPTS-PY marker."
        )
    return ""


def _check_scripts_non_py_drift() -> str:
    """Return an error string when the scripts/*.mjs + scripts/*.sh count on disk
    does not match the <!-- STAT:SCRIPTS-OTHER --> marker in AGENTS.md.

    A mismatch means a new non-Python runner was added (or removed) without
    updating the classification table, prompting the maintainer to classify it.
    Returns empty string when counts agree or the marker is absent."""
    agents_md = ROOT / "AGENTS.md"
    scripts_dir = ROOT / "scripts"
    if not agents_md.exists() or not scripts_dir.is_dir():
        return ""

    live_count = (
        len(list(scripts_dir.glob("*.mjs")))
        + len(list(scripts_dir.glob("*.sh")))
    )
    agents_text = agents_md.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<!-- STAT:SCRIPTS-OTHER -->(\d+)<!-- /STAT:SCRIPTS-OTHER -->", agents_text)
    if not m:
        return "STAT:SCRIPTS-OTHER marker not found in AGENTS.md"
    recorded = int(m.group(1))
    if live_count != recorded:
        return (
            f"scripts/*.mjs + scripts/*.sh count is {live_count} but AGENTS.md "
            f"documents {recorded} "
            f"(drift {live_count - recorded:+d}). "
            f"Classify the new/removed script in AGENTS.md and bump the "
            f"STAT:SCRIPTS-OTHER marker."
        )
    return ""


def _sparkle_build_text(data: dict) -> str:
    """Build the sparkle display text — mirrors build_text() in sync-sparkle-fallback.py."""
    parts = []
    if data.get("emoji"):
        parts.append(data["emoji"] + " ")
    if data.get("label"):
        parts.append(data["label"])
    if data.get("description"):
        parts.append(" \u2014 " + data["description"])
    if data.get("suffix"):
        parts.append(" " + data["suffix"])
    return "".join(parts)


def _check_sparkle_drift() -> list:
    """Return a list of mismatch descriptions when any HTML file's
    [data-sparkle-link] element has drifted from assets/data/sparkle.json.

    Checks both href and text content using the same formula as
    scripts/sync-sparkle-fallback.py (which is the single source of truth).
    Returns an empty list when all files are in sync or sparkle.json is absent."""
    sparkle_json = ROOT / "assets" / "data" / "sparkle.json"
    if not sparkle_json.exists():
        return []

    try:
        data = json.loads(sparkle_json.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"sparkle.json is not valid JSON: {exc}"]

    expected_href = data.get("url", "")
    expected_text = _sparkle_build_text(data)
    if not expected_href:
        return ["sparkle.json missing 'url' field"]
    if not expected_text:
        return ["sparkle.json produced empty text — check emoji/label/description fields"]

    # Regex mirrors sync-sparkle-fallback.py SPARKLE_BLOCK_RE / HREF_RE
    _block_re = re.compile(
        r'<a\b([^>]*\bdata-sparkle-link\b[^>]*)>(.*?)</a>',
        re.DOTALL,
    )
    _href_re = re.compile(r'\bhref="([^"]*)"')

    mismatches: list = []

    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if any(s in rel.parts for s in SKIP_DIRS):
            continue
        html_text = path.read_text(encoding="utf-8", errors="replace")
        if "data-sparkle-link" not in html_text:
            continue

        for m in _block_re.finditer(html_text):
            attrs        = m.group(1)
            text_content = m.group(2).strip()  # strip indentation whitespace

            href_m      = _href_re.search(attrs)
            actual_href = href_m.group(1) if href_m else ""

            if actual_href != expected_href:
                mismatches.append(
                    f"{rel}: [data-sparkle-link] href={actual_href!r} "
                    f"but sparkle.json says {expected_href!r}"
                )
            if text_content != expected_text:
                mismatches.append(
                    f"{rel}: [data-sparkle-link] text mismatch\n"
                    f"    expected: {expected_text!r}\n"
                    f"    actual:   {text_content!r}"
                )

    return mismatches


def _check_glee_dark_coverage() -> list:
    """Return a list of error strings for any GLEE-section light-hex background
    rule in assets/css/theme.css that has no matching dark-mode override.

    Delegates to scripts/check-glee-dark-coverage.py so the logic lives in
    one place.  Returns an empty list when all rules are covered or the script
    cannot run.
    """
    import subprocess
    script = ROOT / "scripts" / "check-glee-dark-coverage.py"
    if not script.exists():
        return []
    result = subprocess.run(
        [sys.executable, str(script), "--require-both"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Parse the output for the individual selector lines
        issues = []
        for line in (result.stdout + result.stderr).splitlines():
            line = line.strip()
            if line.startswith("theme.css line"):
                issues.append(line)
        if not issues:
            issues.append(result.stdout.strip() or result.stderr.strip())
        return issues
    return []


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


def _check_css_token_drift(hashlib_mod) -> list:
    """Return a list of paths whose theme.css?v=<token> does not match the
    current SHA-256 of assets/css/theme.css.

    Uses the same first-8-hex-chars hash as scripts/sync-css-version.py.
    Returns an empty list when all files are in sync or theme.css is absent.
    """
    theme_css = ROOT / "assets" / "css" / "theme.css"
    if not theme_css.exists():
        return []

    expected = hashlib_mod.sha256(theme_css.read_bytes()).hexdigest()[:8]
    token_re = re.compile(r"theme\.css\?v=([^\"' >]+)")

    mismatches = []
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if any(s in rel.parts for s in SKIP_DIRS):
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        for m in token_re.finditer(html):
            if m.group(1) != expected:
                mismatches.append(
                    f"{rel.as_posix()}: token {m.group(1)!r} != expected {expected!r}"
                )
                break  # one report per file is enough
    return mismatches


if __name__ == "__main__":
    sys.exit(main())
