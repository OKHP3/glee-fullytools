# Release CI gate matrix — September 6, 2026

Worker scope: inspect workflow gates and make the PM-approved QA wiring changes.
The PM owns Git integration, commits, push, PR, squash merge, and publication.
No settings, dependencies, action pins, public content, CSS, generators, or
sibling repositories are changed by this worker. Initial inspected HEAD was
`f782ba8097a17d3d0bb6bca8746fe9926f5915d1`; final CI must use the PM's subsequent
integrated head, not that inventory snapshot.

## Required checks and triggers

All seven workflows offer `workflow_dispatch`. Dispatch is not needed for normal
release PR checks. The first four workflows run without path filters on every
PR targeting main and push to main. Preserve their existing job names.

| Workflow and job | Trigger / release role | Native checks actually invoked after this wiring |
|---|---|---|
| Site Validation / `Validate site HTML, links, and structure` | PR/main; weekly Monday 04:17 UTC; manual. Remote-required and repository-required | Check-only generated search/stats/CSS/social/CSP; publication/search/content/artifact/SVG/offline/template/hooks/client/skill/contrast regressions; new six-case CLS suite; validator, links, strict contrast, both branded dark scopes |
| Viewport QA / `Responsive viewport QA (all pages × 8 viewports)` | PR/main/manual. Remote-required and repository-required | Python Chromium full 63×8 viewport sweep; Python inclusive-accessibility suite; newly wired Python representative acceptance with explicit Chromium argument |
| Sparkle Banner QA / `Sparkle banner smoke test (5 pages)` | PR/main/manual. Remote-required and repository-required | Python Chromium Sparkle checks on five pages |
| Resilience QA / `Resilient web behavior (Chromium, Firefox, WebKit)` | PR/main/manual. Repository-required; not in current remote-required contexts | Python full resilience journeys in Chromium/Firefox/WebKit plus Chromium real service-worker lifecycle; newly wired representative Python acceptance separately in each of those three supported engines |
| Publish GitHub Pages / `Validate release commit and build Pages artifact` then `Deploy validated Pages artifact` | Main push or manual only; post-merge exact-event-SHA gate and dependent deployment | Generated checks; explicit CSP and catalog-claim regressions newly added; static publication/search/artifact/offline/contrast checks; Chromium viewport and representative acceptance; three-engine resilience/lifecycle; staged/transfer/final-tar verification |
| i18n Page Sync / `Check translated pages are present and current` | PR/main/manual; not a required context | Configuration-dependent check; `i18n/sync.config.json` absent at inventory, so not evidence of translated-page quality |
| Mermaid Version Watch / `Compare vendored Mermaid against the latest npm release` | Daily 14:53 UTC/manual; maintenance, not release gate | Reads version/registry and has issue-write capability; do not dispatch as routine release validation |

Site Validation also has `Review newer GitHub Actions major versions`, restricted
to schedule/manual events. It does not run on a PR or normal main push and is not
a release requirement. Neither watcher authorizes a dependency upgrade.

The native representative runner explicitly accepts `--browser chromium`,
`firefox`, and `webkit`; default is Chromium. Its checks cover publication
boundaries, real generated-index discovery, modal pointer/keyboard focus,
inline search/history, consent reload, hero contrast and SVG decoding. Invoking
only the default must never be described as three-engine acceptance.

## Observed remote protection

A successful read this worker turn of
`repos/OKHP3/Glee-fullyTools/branches/main/protection` returned these exact fields:

```json
{
  "code_owner_reviews": false,
  "enforce_admins": true,
  "required_contexts": [
    "Validate site HTML, links, and structure",
    "Responsive viewport QA (all pages × 8 viewports)",
    "Sparkle banner smoke test (5 pages)"
  ],
  "reviews": 0,
  "strict": true
}
```

A later duplicate read intended for raw-file export was blocked by socket
permissions; no fresh raw branch-protection JSON was created. The successful
response above is the observed evidence, not a claim that the duplicate passed.
No protection setting was changed. The owner/Architect approval authorizes this
release path; it does not silently alter the documented review policy or add
Resilience to GitHub's required contexts. PM must independently require the
documented Resilience job to pass before merging.

## Approved focused workflow corrections

1. `validate.yml`: one new step runs
   `node --test scripts/tests/test-cls-session-window.cjs`. The six tests import
   the pure accumulator without loading Playwright; existing runner Node is used.
2. `viewport-qa.yml`: invokes `test_browser_acceptance.py --browser chromium`
   before merge, and uploads its JSON with existing viewport/inclusive evidence.
3. `resilience-qa.yml`: invokes the same runner with each supported engine already
   installed by that job. It keeps separate JSON filenames, attempts all three,
   and returns nonzero if any engine fails. Reports join the existing upload.
4. `pages.yml`: adds `check-csp.py` and `test_content_claims.py` to the exact-merge
   static gate, so Pages does not rely solely on earlier PR checks for them.

Native dependencies/install commands and job names remain unchanged. No gate
was weakened and no branch Pages dispatch was performed. The corrected shell
loop uses `|| failed=1`, then exits with the accumulated status; it does not turn
an individual failure into a successful overall job.

Local verification: action-version checker passed all seven workflows; CLS
tests passed 6/6; whitespace checks passed. `actionlint`, Python PyYAML and Node
`yaml`/`js-yaml` are unavailable in the installed runtime. Workflow edits were
reviewed structurally, but a dedicated YAML/actionlint pass is NOT RUN. No
dependency was installed to obtain one. Native browser execution and GitHub
workflow parsing remain exact-head CI evidence to collect, not a local pass.

## Exact-head commands and evidence

The PM supplies the PR number and full head SHA after committing these changes.
Use read-only commands first:

```powershell
gh pr view $releasePr --json number,url,headRefOid,baseRefOid,mergeStateStatus,statusCheckRollup
gh pr checks $releasePr --json name,state,bucket,workflow,link
gh run list --commit $releaseHead --json databaseId,workflowName,event,headSha,status,conclusion,url
gh run view $failedRun --json headSha,event,status,conclusion,jobs,url
gh run view $failedRun --log-failed
```

PR Actions normally check out the synthetic PR merge ref. Record both the PR
head/base and run association; do not confuse that test commit with the final
squash SHA. After authorized squash merge, collect all main-push validation
results and the Pages event SHA. Pages explicitly compares checked-out HEAD to
`github.sha`; artifact provenance must identify that final release SHA.

On failure, preserve the exact failing run, logs and uploaded reports under
`assets/audit/release-2026-09-06/`. Reproduce the failing condition, identify a
source or test-harness defect, and coordinate a focused correction before PM
commits and pushes. Do not repeatedly rerun an unchanged deterministic failure,
relax thresholds, hide errors, or infer that a missing engine passed.

Normal PR creation triggers the required jobs automatically. If a job is missing,
inspect trigger/event/permissions and the run association before a targeted
nondeployment dispatch. A dispatch uses the selected branch ref, which can move;
check its returned SHA. Do not manually dispatch Pages from the task branch.

## Remaining coverage boundaries

Local handoff correction: the platform report now isolates report-writing
checks in an exact-SHA **local clone**, not a Git archive. PM preflight showed
that `csp.py` needs `git ls-files`; the plain archive produced exit 128 despite
63 issue-free HTML results. The clone preserves Git metadata and keeps report
writes outside the source checkout, without remote fetching or installation.
The PM owns execution of the corrected clone preflight; this worker only
validated the revised PowerShell syntax and did not rerun those checks.

- Pages still runs its representative acceptance in Chromium only; the PR and
  main-push Resilience jobs provide the added three-engine representative gate.
  Pages itself independently runs three-engine resilience, not three-engine
  representative acceptance. Pages does not rerun inclusive-accessibility QA;
  the Viewport job owns that gate before and after merge.
- Supplemental Node focus/performance/search fixtures are local evidence, not
  automatically invoked browser CI. Their corrected CLS algorithm now has a
  durable pure regression step. Native acceptance and inclusive/resilience suites
  are the browser CI contracts; these are not equivalent to every local fixture.
- Pages advisory audit and live-header smoke are explicitly nonblocking. Review
  their actual output. Missing HTTP-only controls remain a host limitation.
- A green required-context list alone is insufficient: Resilience, main-push
  exact-SHA jobs, Pages validation/deployment, transferred public hidden files,
  release provenance and independent live acceptance all remain distinct gates.
- Lab/fixture tests do not certify external GPTs, provider retention, fonts under
  real network conditions, field Core Web Vitals or third-party services.
