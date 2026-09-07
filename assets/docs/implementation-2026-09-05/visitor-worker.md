# Visitor truth implementation

Date: 2026-09-05. Worker: `/root/visitor_truth`, reporting to the implementation PM.

Worktree: `C:/Users/jamie/.codex/worktrees/73b4/glee-fullytools`.
Branch: `codex/assessment-corrections-20260905`.
PM-confirmed baseline: `5da805785d47f9bc29058b07d2a5467da32a1573`.
No worker commit or staging operation; the PM owns serialized integration and commits.

## Implemented locally

- A03: Replaced 11 unreviewed external anchors with internal detail routes. These cover the eight originally identified bypasses, another withdrawn Detour Discoverer branch link, and two Critter Spotter branch links whose alternate destination ID does not match the retained detail-page destination. No external destination was restored or invented.
- All 17 unavailable branch cards now show an unavailable label and retain a usable detail route. Unavailable detail pages no longer tell visitors that their withdrawn action opens ChatGPT. Existing professional-care boundary copy is preserved.
- A04: Replaced Scheduling Wizard's full authoring scaffold with a short unavailable concept brief, using the existing metadata and September 4 register's tasks/bills/events/calendar-ready-plan definition. It explicitly leaves calendar integration, reminders, exports, and external GPT behavior unverified. Its branch description and metadata now agree with that brief.
- The stronger scaffold scan also found and corrected leftover author instructions in Resume Customizer, Care Check, Snappy Count, and Critter Spotter. These replacements summarize the existing page purpose without adding functionality.
- A12: Aligned the Identity Known Toolbox card, bLinkIn Tuner branch card, and Maven Wise branch card with their reviewed detail identities. Qualified Toolbox shared-memory/context claims, Persona tone-configuration claims, and Moody Log's private-storage/guardrail assertions as intended or unverified. Added the third-party data boundary beside Moody Log's launch action.
- A13: The homepage's “Explore the full toolbox” reaches `/toolbox/`. The Toolbox hero has a primary branch-browse action and explicitly names its separate external Toolbox GPT action.
- Expanded the promise audit to inspect every public GPT anchor, detect unknown destination IDs and label/identity mismatches, reject public authoring scaffold, and reject conflicting unavailable/launch instructions. Existing `launch_urls(html)` and `publication_state(html, urls)` behavior and interfaces remain unchanged for their consumers.

## Evidence

The PM established the pre-edit site baseline: validator 63 files / 0 issues / 0 warnings; link checker 2,690 internal links / 0 broken / 60 sitemap URLs.

The new test file was executed before implementation: two content failures and five missing-check errors reproduced the homepage/scaffold defects and absent audit safeguards. After adding the audit but before HTML fixes, it reported the 11 external-route discrepancies, unavailable launch-help contradictions, and additional scaffold remnants.

Final focused checks use the bundled interpreter at `C:/Users/jamie/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` with `PYTHONUTF8=1`:

| Check | Result |
|---|---|
| `scripts/tests/test-visitor-truth.py` | 9 tests pass: secondary withdrawn link, wrong identity with otherwise allowed URL, allowed secondary/internal routes, generic/placeholder URLs, visible scaffold vs. comments, homepage CTA, Scheduling scaffold, complete catalog audit/counts, and all unavailable branch-card detail routes |
| `scripts/audit-tool-ette-promises.py` | Pass; 42 pages, 1 live, 24 beta, 17 unavailable; all public GPT entry points agree with primary destinations |
| `scripts/tests/test-reconciliation.py` | 3 tests pass; existing launch-classification API retained. Existing temporary server test emits a non-failing ResourceWarning; its expected stale-cache negative case prints an error before the asserted repair passes. |
| `git diff --check` on owned sources | Pass using repository line-ending handling; suppressing safe-CRLF warnings does not change tracked configuration |

`py -3` points to a missing Python 3.14 executable on this host, and `py -3.13` is inaccessible here. No interpreter or dependency was installed. The bundled runtime completed the checks.

## Exact source ownership

Changed HTML:

```text
index.html
persona/index.html
toolbox/index.html
toolbox/01-discovered-careers/index.html
toolbox/01-discovered-careers/01b-resume-customizer/index.html
toolbox/01-discovered-careers/01e-blinkin-tuner/index.html
toolbox/01-discovered-careers/01f-career-seeker/index.html
toolbox/02-treasured-finds/index.html
toolbox/02-treasured-finds/02d-scentinal-journal/index.html
toolbox/02-treasured-finds/02e-spirited-journal/index.html
toolbox/03-tasty-tracker/index.html
toolbox/03-tasty-tracker/03b-menu-conductor/index.html
toolbox/03-tasty-tracker/03d-pantry-shopper/index.html
toolbox/04-travelers-guide/index.html
toolbox/04-travelers-guide/04c-detour-discoverer/index.html
toolbox/05-organized-life/index.html
toolbox/05-organized-life/05d-scheduling-wizard/index.html
toolbox/06-healthy-bee-ing/index.html
toolbox/06-healthy-bee-ing/06a-care-check/index.html
toolbox/06-healthy-bee-ing/06b-calm-keep/index.html
toolbox/06-healthy-bee-ing/06c-snappy-count/index.html
toolbox/06-healthy-bee-ing/06d-medi-minder/index.html
toolbox/06-healthy-bee-ing/06e-moody-log/index.html
toolbox/07-identity-known/index.html
toolbox/07-identity-known/07a-critter-spotter/index.html
toolbox/07-identity-known/07c-sight-seeker/index.html
toolbox/07-identity-known/07d-snap-decoder/index.html
toolbox/07-identity-known/07e-motif-muse/index.html
toolbox/07-identity-known/07f-maker-matcher/index.html
toolbox/07-identity-known/07g-self-fixer/index.html
```

Other changed/new files: `scripts/audit-tool-ette-promises.py`, `scripts/tests/test-visitor-truth.py`, and this report. No shared runtime, CSS, generated data, cache tokens, workflows, or publication-state register was edited by this Worker.

## Integration and limits

The PM must regenerate search/statistics/cache outputs in order, rerun site/link gates, and verify real-browser browse and unavailable-detail journeys. This Worker reports local source/test evidence only, with no publication, live-site verification, external GPT behavior test, or PR22 changes.

The deterministic audit reconciles public links against the current primary destination identities; it does not supply owner authorization for a new primary destination. New destinations still require the existing review process. Taxonomy, 42 routes, publication counts, schema pricing/screenshot fields, feed/date policy, broader claim audits, and external capability decisions retain their existing owner boundaries.

## Python browser acceptance gate addendum

The PM later assigned this Worker one additional file: `scripts/tests/test_browser_acceptance.py`. It is an explicit Python Playwright gate against a running site (`--base-url`, default `http://localhost:5000`), with optional browser, JSON-output, and screenshot arguments. The PM owns its workflow wiring. The Browser plugin/skill is unavailable in this session; regular Playwright is the explicitly requested CI path.

The flow under test is: homepage/search/legal/detail route → visitor interaction or theme state → correct visible result, URL, focus, consent status, and healthy first-party resources.

Nine named checks cover:

- Actual served generated search JSON (60 entries and 1/24/17 states), plus deep-function discovery.
- Glee modal identity, local suggestions, unavailable result labeling, up/down/Enter navigation, and Escape focus return.
- Inline query, section filter, Back/Forward, reload, keyboard destination, and 1280/375-pixel overflow checks.
- Default-off consent, saved grant after reload, saved denial after reload, and zero transmitted measurement requests. All third-party browser requests are blocked; attempted measurement loads are counted separately.
- Four computed hero contrast states: explicit light/dark and automatic light/dark. Eyebrow must reach 4.5:1; the measured large heading must reach 3:1. Transparent backgrounds or unexpectedly small headings fail rather than receiving an unsupported ratio claim.
- Actual Neighborly Bazaar SVG decode and nonzero dimensions on its detail route.

Every journey fails on uncaught page errors, first-party HTTP failures, failed first-party requests, or first-party console errors. It blocks service workers so stale browser caches cannot hide the current generated release; the separate resilience gate remains responsible for offline behavior.

Local authoring validation passed: Python source compilation, dependency-free `runpy` import, white/black/same-color contrast math, and precise measurement-host matching. Playwright imports are deferred until CLI execution, so unittest discovery does not require the optional browser dependency. The CLI was deliberately executed and returned a failing JSON result for `No module named 'playwright'`, with no static substitute or dependency installation. The PM also confirmed its other inspected Python runtime lacks Playwright. Browser execution of this new Python runner is **not verified locally**; its locators and journeys were reviewed against the existing Node Playwright runners, whose separate results are not represented as a Python-runner pass.

The CI command after the existing server startup is:

```text
python3 scripts/tests/test_browser_acceptance.py --base-url http://localhost:5000 --output assets/audit/browser-acceptance.json
```

No workflow, runtime, generated file, or other source was modified for this additional assignment.
