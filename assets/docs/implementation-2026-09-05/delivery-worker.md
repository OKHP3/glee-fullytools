# Delivery and resilience implementation

Date: 2026-09-05. Worker: `/root/delivery_resilience`, reporting to Implementation
PM `/root`. Shared worktree: `C:/Users/jamie/.codex/worktrees/73b4/glee-fullytools`.
Branch: `codex/assessment-corrections-20260905`. Reviewed source baseline:
`5da805785d47f9bc29058b07d2a5467da32a1573`. No Worker commit, staging, push,
deployment, dependency installation, or external write was performed. The PM
owns integration commits and final generated output.

## Owned changes

- `.github/workflows/pages.yml`: replace repository denylist copying with the
  reviewed public allowlist; verify before upload, after download against the
  same release checkout, and in the final Pages tar before deployment. Both
  upload boundaries preserve the reviewed hidden public files.
- `scripts/public-artifact.py`: standard-library-only staging and complete
  file/byte/provenance verification, local-reference checks, and archive checks.
  Reject unexpected staged files/directories, symlinks/reparse points, archive
  links/path escapes, missing required files, changed bytes, and commit mismatch.
  Existing staging content is never recursively deleted or overwritten.
- `sw.js`, logic only: cache reads/writes are best effort; cache failures do not
  replace valid online responses. Eligible successful public HTML navigation
  stores one query-free shell per pathname. Serialized writes retain at most
  80 non-precache navigation entries, preserving the intentional offline shell.
  Other paths and third-party requests are not retained. Generated cache name,
  asset tokens, and precache entries remain PM-owned.
- `scripts/tests/test_public_artifact.py`,
  `scripts/tests/test-sw-resilience.cjs`, and
  `scripts/tests/test-sw-browser.cjs`: focused inventory/transfer, deterministic
  production-worker, and real Chromium worker regressions.
- `docs/resilience.md`: describe the actual offline/cache/artifact boundary and
  executable test coverage. No hosting/header capability is implied.

## Reviewed public allowlist

PM approved before workflow/source changes: public root HTML and web-standard
files, CNAME, `.nojekyll`, `.well-known/security.txt`, the ten public HTML route
directories, runtime CSS/JavaScript, exactly `search-index.json`, `sparkle.json`,
and `icon-map.json`, image assets, and vendored Mermaid modules/license/version.
Visitor downloads require an explicit filename; the current empty download
allowlist excludes its placeholder. Templates, audit/docs, brand profiles,
agent/skill content, source tooling/configuration, and root Markdown are excluded.
The source files themselves are preserved.

Inspection of the actual [Pages v5 action](https://raw.githubusercontent.com/actions/upload-pages-artifact/v5/action.yml)
confirmed that its tar step independently excludes hidden paths by default.
Therefore `include-hidden-files: true` applies to both generic artifact upload
and Pages upload, solely over the already verified staging directory. Final tar
inspection catches a future accidental loss at the second boundary.

## Verification performed

- Before source repairs, repository validation passed: 63 pages, zero issues,
  zero warnings; link check passed with 60 sitemap URLs and zero broken links.
  Native `py -3` points to a missing Python 3.14 executable; tests used the
  preinstalled bundled Python and Node runtimes instead.
- Before SW logic edits: 9 deterministic tests, 2 pass / 7 fail. Failures proved
  quota/open failures discarded valid network content, query variants grew the
  cache, non-public paths were cached, asset storage failure discarded network
  access, and the cold-offline adapter was absent.
- After SW logic edits: 8 of 9 deterministic tests pass. The single pending
  test requires the PM to add `/assets/js/glee-site-enhancements.js` to the
  intentional precache and regenerate the cache version. No generated list
  entry was edited by this Worker.
- Public-artifact fixture suite: 11 tests, 10 pass / 1 skipped. The skipped
  test requires creating a real symbolic link, which this Windows host denies;
  it will execute on a host permitting symlink creation. Missing security.txt,
  unexpected hidden content, modified bytes, wrong provenance, broken public
  references, excluded development links, and hidden files lost in the final
  tar are covered. The new harness was first run before its implementation and
  failed because the staging module did not yet exist; it is new coverage.
- Current-tree staging passed: 711 files, 63 HTML pages, 208,395,611 bytes;
  `.nojekyll` and `.well-known/security.txt` present. Local page, asset, sitemap,
  manifest, precache, and search-index references resolved. The shared runtime's
  inactive French-index and AskJamie-adapter branches are excluded from reference
  requirements only when no matching public locale/brand page exists.
- Existing workflow action-version policy and static resilience checks passed.
  Scoped `git diff --check` passed. No YAML parser package is installed in the
  inspected bundled Python/Node runtimes; none was installed for this task.
- Real Chromium source journey passed actual quota-write and unavailable-storage
  injections while retaining online pages, and 12 query navigations retained one
  search shell. It then failed at the expected missing-adapter precache assertion.
  The runner explicitly registers the worker to isolate lifecycle behavior;
  automatic adapter registration timing is not certified by this test.

## Integration and remaining evidence

PM must insert the adapter precache entry, run the serialized generators, and
rerun both SW suites. The Chromium runner clears ordinary HTTP cache before
the offline journey and requires the adapter response to come from the worker;
it then verifies search query/results, an uncached fallback, and reconnect.
`PUBLIC_SITE_DIR` can run it over the staged artifact. Repeat artifact staging
after final integration, because byte comparison intentionally detects any
later source change.

The dynamically loaded adapter currently subscribes to window `load` to register
the worker; a late import can miss that event. This was referred to the Runtime
Worker through the PM for a readyState-aware registration fix. Initial automatic
registration runs did not yield a controlling worker; direct registration made
the focused worker tests execute. That observation alone does not establish
the frequency or sole cause of the timing issue.

All results above are local implementation evidence. The actual GitHub artifact
transfer, deployed security.txt, live release provenance, excluded development
URLs, and hosted behavior remain unverified until an owner-authorized release.
Broader browser/error-gate expansion, dependency/action pinning, hosted security
headers, and deployment settings remain outside this Worker's scope.

## Independent review correction

The PM's independent review found that tar directory entries were skipped before
path validation. A focused reproduction confirmed that traversal, absolute,
unexpected ordinary, and unexpected hidden directory entries were accepted.
The archive verifier now checks every member's path before its type, then allows
directories only when they are expected parents of public files (including the
tar root `.`). No extraction occurs. All four negative cases now pass, and the
full public-artifact suite passes 12 tests with only the existing Windows
symlink-creation test skipped (11 pass / 1 skip).
