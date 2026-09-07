# Translation transition: leftovers, current tooling, and cleanup

Date: 2026-09-05. User direction: translation prototyping is moving toward pair-specific Agent Skills and Python/GitHub automation; inspect leftovers from the earlier i18n approach without discarding current work.

Local source remains `5da805785d47f9bc29058b07d2a5467da32a1573`. Current remote main was checked at `9b4ade05dbe6f8c755f20c2e7bc2e19b03da1b47`, after PR #22 merged. This review did not move the checkout, overwrite another task, or publish.

## Result

Removed the confirmed local migration debris: five obsolete top-level translation-skill directories containing five ignored `.DS_Store` files and one ignored Python bytecode cache. There were no tracked source files in any of those old directories. The active five skill packages under `.agents/skills/language-mediation/` are intact.

All five translation-package suites passed, ten tests each. The page-sync suite also passed ten tests: **60 tests passed**. These tests validate package behavior and deterministic controls, not language quality or external publication.

The remaining browser i18n code needs an explicit configuration boundary, not indiscriminate deletion. Shared stylesheet/menu functionality was just maintained in PR #22; it is not abandoned merely because this Glee clone does not display a language menu.

## What is current versus residual

| Surface | Observed state | Disposition |
| --- | --- | --- |
| `.agents/skills/language-mediation/okhp3-translation-en-us-*` | Five active pair-specific packages: de-DE, en-GB through the en-uk-named package, es-ES, es-MX, fr-FR; planners, validators, controls and tests present | Keep |
| `.agents/skills/okhp3-i18n-page-sync/` | Active deterministic source/target drift detector; names the matching translation skill; does not translate | Keep |
| `.github/workflows/i18n-page-sync.yml` | Invokes that Python detector; missing config deliberately returns success with `configured: false` | Keep; explain inactive pilot scope honestly |
| `i18n/sync.config.json` and sync ledger | Absent locally and on checked remote main | Not configured; do not invent pilot routes, target locales, or an adoption ledger |
| Translated page roots and locale indexes | No `/fr/`, `/de/`, `/es/`, `locales/`, `translations/`, or translated search index on the checked remote tree | No translated public content to delete |
| Production language links/menus | No `hreflang`, `.lang-switch` markup, or `/fr/`, `/de/`, `/es/` navigation links found in the 63 local production HTML pages | No currently shipped locale-menu dead end found |
| Shared menu JavaScript and CSS | Dormant on Glee's current markup; PR #22 maintained compact viewport layout | Preserve until a coordinated shared-interface decision |
| Shared search locale assumptions | `app.js:586-593` assumes a French index exists, collapses regional tags, and special-cases German/Spanish fallback | R12 follow-on: configure explicitly per consuming site |
| Five old top-level translation directories | Only ignored OS/cache debris, no tracked files | Removed in this review |
| Historical translation benchmarks/examples | Located inside active packages; identified as historical/example material | Preserve evidence and controls; not deployed translation outputs |

Evidence: `translation-cleanup.json` records exact removed paths, byte counts and SHA-256. `translation-remote-inventory.json` records the untruncated remote tree check and workflow inventory. Both are under `assets/audit/assessment-2026-09-05/`.

## Actual automation boundary

The current Glee workflow does not autonomously generate translations. It runs:

```bash
python3 .agents/skills/okhp3-i18n-page-sync/scripts/i18n-page-sync.py --root . --mode check
```

With no consuming-site config, the current JSON result is `configured: false`. The green job proves its intentional unconfigured behavior, not that any translated page exists or is current.

When explicitly configured, the detector compares in-scope source pages with target files/ledger hashes and names the responsible exact-pair skill. An agent or human runs the translation stage, reviews the draft, and explicitly adopts the relevant route baseline. The skill's planner/validator is support tooling; its presence does not mean GitHub Actions invokes a model or produces translated prose. No new external API, credential, or translation run was introduced by this cleanup.

Static translated pages still need deliberate routes, `lang`, optional language navigation, accurate alternates, search coverage, and publication state once they exist. Those delivery concerns remain relevant even when the drafting method changes from the older i18n process to Agent Skills.

## R12 integration design

The PM received a follow-up assignment to add translation cleanup to the existing work packages and coordinate it with R2 search ownership.

1. Preserve the current five pair skills and Python drift detector. Use the nested language-mediation package paths in future instructions. The removed directories were not compatibility wrappers.
2. Replace shared site-specific comments claiming four pilot routes and reviewed French coverage with accurate capability comments when the shared runtime is next touched.
3. Move locale-to-search-index and publication/fallback policy into a small consuming-site configuration or adapter. Glee currently declares only its English catalog. Do not infer an existing French index from `html.lang` alone or from another site's publication status.
4. Retain region information for exact pairs. Do not collapse `es-ES` and `es-MX` or any future French regional pair before looking up the declared route/index contract.
5. A menu should offer only explicitly declared real destinations. Keep shared disclosure mechanics available for sites that use them; do not add empty selectors/menu controls to Glee pages.
6. Test English-only startup without locale requests, a configured locale with a real index, an unavailable/failed locale index with a truthful fallback, regional pair distinction, and no advertised links to missing pages. A missing locale must never silently become a quality-approved translation.
7. Recheck the now-merged PR #22 before R2/R12 integration. The local audit baseline is older; source comparison confirms app.js was unchanged by that PR, while CSS and offline shell changed. Do not reapply its compact-menu patch or remove it just to clean up this clone.

This is a localized interface refinement to prepare alongside the already-assigned search work. A broad cross-site rewrite or deletion of the shared language menu remains outside this cleanup. The PM's exact ownership/dependencies are recorded in `pm-assessment-and-work-packages.md`.

## Validation and preservation

- Pre-delete gate: every removed file was ignored by Git; all five roots contained zero tracked files; contents were limited to known Finder/Python-generated artifacts; no symlinks or other source files were present.
- Deletion used exact verified files and removed directories only after empty. No recursive blanket deletion or source-art removal.
- Five active package suites: 50/50 PASS. Sync detector suite: 10/10 PASS. Suite adoption operations happened only inside test-created temporary fixtures, not the real site ledger.
- Actual site check: detector reports not configured. No adoption, translated-content generation, index regeneration, or publication occurred.
- Existing assessment files remain intact. Source clone tracked diff remains empty apart from any separately documented future work; this review adds assessment evidence and removes ignored debris only.
