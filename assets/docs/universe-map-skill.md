# Automatic universe maps

The canonical package is `OKHP3/skillz/mermaid/okhp3-universe-map`, version 0.1.4. The local `.agents/skills/okhp3-universe-map` copy is installed without changes to its core files. Site configuration belongs in `universe-map.config.json`.

Canonical source revision: `9d3677ad89f51d68ec946174f9ddff1c1f3f5b53` (Skillz PR 79). All 12 installed files were compared directly with that immutable Git tree.

## Active integration

`build-search-index.py` regenerates the local index, then invokes `sync-universe-map.py`. The adapter generates in memory, replaces exactly one `AUTOGEN:UNIVERSE-MAP` block in `universe/index.html`, and writes `assets/data/universe-map.json` for coverage and source hashes. There is no growing staging directory to prune as pages disappear.

The indexer strips the generated block before parsing. Unchanged inventories retain their generation timestamp; changed inventories use the Git revision timestamp so independent release jobs reproduce identical files. The release pipeline runs index, portfolio statistics, index again, then cache synchronization before validation and packaging. The deployment job repeats that same deterministic generation before comparing artifact bytes against its exact checkout.

The public view has a three-brand overview and local detail groups. Sibling links open the other sites' current universe pages. No peer inventory is copied, so this view needs no cross-repository token, periodic fetch, or refresh trigger. The historical hand-authored concept map is preserved in `docs/archive/universe-concept-map-2026-09-06.md`; absent ideas are not assigned invented lifecycle states.

Tool-ette states come from the existing `audit-tool-ette-promises.py` publication contract. Published page does not mean a verified or completed GPT. The package supports explicit planned concepts in configuration when the owner supplies that decision.

## Rendering and accessibility

`assets/js/universe-map.js` renders expanded groups in strict Mermaid mode. It adds same-origin SVG links from the ordinary linked outline, without enabling Mermaid callbacks. Graphs scroll within their panels on small screens. Ordinary links work with JavaScript disabled or Mermaid unavailable. Theme changes regenerate the visible diagrams.

## Checks

- `py -3 -X utf8 scripts/build-search-index.py --check`
- `py -3 -X utf8 scripts/sync-universe-map.py --check`
- `py -3 -X utf8 scripts/tests/test-universe-integration.py`
- `py -3 -X utf8 .agents/skills/okhp3-universe-map/tests/test-universe-map.py`
- `py -3 -X utf8 scripts/tests/test-universe-browser.py` with the release Playwright runtime and a local server on port 5000; `UNIVERSE_BASE_URL` can select an owned preview server.

`assets/audit/universe-map/` retains generator-only staging evidence. The public page and `assets/data/universe-map.json` are the active release outputs.


### Portable skill 0.1.4

Includes the final PR76 hierarchy fix for slashless URLs, explicit-parent handling for ambiguous slash aliases, and validated trusted local index paths. All 19 generator regression tests pass. Existing indexed page links and rendering are preserved.
