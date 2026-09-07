# Platform and release handoff — September 5, 2026

This is a local release proposal and evidence record, not approval to publish,
change hosting, upgrade dependencies, or synchronize sibling repositories.
The reviewed initial implementation is `8dea009c7b1887b129a1c5540ec1a39f6c028841`.
This wave started at `f5f33986e6ee287fb165c75e82ef01e5d3ed1f99`, which includes
the initial implementation and main/PR22. The PM must record the final commit
after integrating this wave; working-tree evidence below is not exact-commit
release acceptance. Original assessment IDs A16–A18 remain traceable here.

## Scope and current evidence

| Claim | Tier | Evidence | Consequence if false | Next check |
|---|---|---|---|---|
| Public artifacts use an explicit inventory, including both hidden public files | Confirmed source | `scripts/public-artifact.py`, `pages.yml`, initial artifact tests | Development content could publish or security contact disappear | Run actual GitHub upload/download and final tar assertions on release SHA |
| Current Python can run the standard-library static checks | Confirmed local | Python 3.12.14; search check 60, validator 63/0/0, links 63/0 broken/60 sitemap | Local checks could be overstated | Repeat final commit; run CI Python 3.11 |
| Python browser suite ran here | Unknown / did not run | `playwright` unavailable in bundled Python | Missing cross-browser CI evidence | Execute existing Python workflows on GitHub |
| Node Chromium and WebKit are usable locally | Confirmed local | `assets/audit/remaining-program-2026-09-05/platform-*.json` | Focus regression may remain | Final integrated browser run |
| Firefox website behavior passes | Unknown | Firefox process launches but page creation throws `Cannot read properties of undefined (reading '_page')` | Firefox-specific failures remain undiscovered | Matched supported Playwright/browser runtime in CI |
| Current remote rule enforces an approving/code-owner review | Confirmed false | September 5 branch protection GET: 0 approvals, code-owner review false | Policy could be bypassed | Owner chooses and verifies settings |
| Source tests establish deployment/live acceptance | Confirmed false | No publication action in this wave | A stale or malformed public release could go unnoticed | Exact-SHA release checks below |

Installed runtime paths, verified without installation:

- Python: `C:/Users/jamie/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`
  reports 3.12.14. `import bs4` raises `ModuleNotFoundError: No module named 'bs4'`;
  `importlib.util.find_spec('playwright')` returns `None`. The current search,
  validator, and link scripts do not import BeautifulSoup, so their successful
  runs do not establish BeautifulSoup availability. Earlier environment claims
  must not override these direct imports.
- Node: `C:/Users/jamie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe`
  reports 24.19.0; adjacent `node/node_modules` contains Playwright 1.62.1.
- Installed browsers: Chromium revision 1234, Firefox 1538, WebKit 2336 under
  `C:/Users/jamie/AppData/Local/ms-playwright`. Firefox's page-creation failure
  also occurs outside the site harness. No browser download or runtime repair
  was attempted. Package and browser versions must be paired per
  [Playwright's browser documentation](https://playwright.dev/docs/browsers).

The Node runner serves real source files and the checked-in search JSON, records
SHA-256 of served bytes, blocks third parties and service workers, and removes
only `upgrade-insecure-requests` from local HTTP HTML responses. Its focused
journeys are supplemental; they do not replace the full Python viewport,
inclusive, or resilience suites, hosted font checks, or service-worker tests.

## Focus corrections and local change inventory

The PM extended this worker's assignment to two localized changes in
`assets/js/app.js` and one line in `.github/workflows/validate.yml` that invokes
the Content Worker's `scripts/tests/test_content_claims.py`. No other workflow,
dependency, adapter, builder, generated asset, or sibling source was edited by
this worker. The runtime diff captures the explicit pointer opener, cancels and
guards deferred input focus, focuses valid fragment targets with a temporary
tabindex, records fragment history, and honors reduced motion. It does not
change the browser's Tab key policy.

`platform-focus-before.json` records 20 passing and four failing checks before
the correction: skip focus failed in Chromium and WebKit, and WebKit pointer
search focus failed both on the homepage and after dismissing the construction
notice. Keyboard button activation and Ctrl+K already passed. This isolates the
pointer-focus assumption rather than blaming the construction dialog. The
immediate-close case is a preventive regression and did not fail beforehand.

The installed Windows WebKit excludes ordinary anchors from native Tab order
even in an isolated HTML fixture; the probe selects the button after the link.
Raw probes and the failed intermediate attempts are retained. The final test
requires focus on main in both engines and next-link navigation in engines whose
native Tab includes links. WebKit next-link coverage remains explicitly NOT RUN;
the site must not override all link tabindex values to mask that runtime setting.
Chromium verifies both main focus and the next Tab landing inside main.

Final focused evidence is `platform-release-final.json`: 26 named checks passed
in Chromium/WebKit, with the WebKit next-link coverage limitation above. All JSON evidence lives
under `assets/audit/remaining-program-2026-09-05/`. It fingerprints the actual
served working-tree bytes, which can differ from the report's baseline HEAD.
Existing analytics/iframe regressions, action policy (seven workflows), catalog
claim audit (42 pages, zero errors), content claim tests (eight), and artifact
tests (12: 11 pass, one Windows symlink-privilege skip) also passed locally.

Documentation corrections cover `replit.md`, `scripts/README.md`, deployment,
release governance, roadmap, companion contract, and ADR-0004. This report and
`pr-draft.md` are new. `docs/threat-model.md` required no additional edit.

## A17: Exact source and target promotion proposal

**Proposal:** retire timestamp selection as authorization. The existing
`scripts/sync-foundation-files.py` may be inspected in dry-run mode; its `--apply`
and `--commit` modes choose the newer commit when two content groups differ.
Neither recency nor agreement of two repositories proves which behavior is
correct. No sibling write or synchronizer mutation is included in this wave.

Read-only target inventory on September 5:

| Repository | Checked-out commit | Working-tree condition |
|---|---|---|
| Glee-fully Tools, reviewed initial source | `8dea009c7b1887b129a1c5540ec1a39f6c028841` | Accepted source snapshot; this wave changes app.js again |
| OverKill Hill | `bd11085dc639481fc52933221384f552b5825ae6` | Untracked `.playwright-cli/`; not a clean promotion target |
| AskJamie | `1d969b6c191a67ea75579901ca28b313dff0248b` | Clean at observation |

Both sibling mirrors were read at
`C:/Users/jamie/OKH-Local/04_GitHub_Mirrors/{overkill-hill,askjamie}`.
These are observed local heads, not an assertion of current remote convergence.

| File | Initial Glee source Git blob | Both observed target Git blobs | Proposed disposition |
|---|---|---|---|
| `assets/js/app.js` | `a943c5110630b8141dd2c31aa4d1ca3fe19573a6` | `5ddad63558afe6c5299313238204d09712aaf294` | Review search retry/loading, accessible results, focus, and shared behavior by hunk; preserve site-specific initialization |
| `assets/css/theme.css` | `88034c9b3fc6ec2be23b6b033ee61f6b8defc999` | `1b573355c73aaf3633446b1f6472fa9f9c63d0d6` | Select shared search/focus styles only; retain brand scopes and target fixes |
| `assets/js/mermaid-init.js` | `420effa94deb78302090e3369e45c1bc8d315dea` | `420effa94deb78302090e3369e45c1bc8d315dea` | No-op; do not rewrite equal bytes |

An executable future promotion must consume an owner-reviewed manifest with:
source repository + full commit + path + blob; target repository + expected
HEAD + expected preimage blob; approved patch hash; allowed changed paths;
site-specific exclusions; target validation commands; resulting blob hashes.
The PM must replace the source app.js commit/blob with the final accepted
focus-correction commit before proposing those additional hunks. Never pair the
old source commit with new working-tree bytes.

Required failure behavior: stop before any write for a dirty/unknown target,
changed HEAD/preimage, missing source ref, unreviewed path, path escape/link,
divergent third version, failed patch context, missing dependency, or failed
validation. Equal output is a no-op. Partial patch application must fail as a
unit in an isolated branch, preserve evidence, and never auto-commit or force
copy. Preserve target changes instead of selecting by timestamp. Each sibling
needs its own review, generated-data refresh, tests, PR, and live acceptance.

Acceptance cases for that future executor: exact accepted pair applies only
approved hunks; changed source/target hash refuses; newer but unapproved content
refuses; both possible two-group arrangements refuse without a manifest; third
content group refuses; dirty/untracked target refuses; CSS brand sections and
site adapter remain byte-identical; repeated application is a no-op; generator
or browser failure prevents publication. This document specifies those cases;
no replacement executor or passing test for one is claimed.

## A18: Toolchain and dependency decision inventory

Current source policy remains unchanged. Pin migration is a coordinated future
change, not an incidental release prerequisite introduced by this document.

| Surface | Current source | Recommended owner decision and provenance |
|---|---|---|
| Python CI | Python `3.11`; unpinned `beautifulsoup4` and `playwright` installs | Adopt reviewed requirements with transitive hashes and explicit update cadence; first determine whether BeautifulSoup is still needed by active jobs |
| Python browser candidate | No Python Playwright installed locally | PyPI Playwright **1.62.0**, July 31, 2026, Python >=3.10; evaluate against all existing runners before pinning. It is not bundled Node 1.62.1 |
| BeautifulSoup candidate | No BS4 installed locally | PyPI BeautifulSoup4 **4.15.0**, June 7, 2026, Python >=3.7; removal or retention is a separate tested dependency decision |
| Optional Node QA | `puppeteer ^25.9.0`, `lighthouse ^13.4.1`; lock resolves those exact versions/integrity | Keep the lock; choose documented Node >=22.19 for both tools. Puppeteer requires >=22.12 and Lighthouse >=22.19 |
| Replit runtime | `nodejs-20`, `python-3.11`, Nix `stable-25_05` | Choose a supported compatible Node module or explicitly retire optional Node QA there; no runtime config change here |
| CI Node | Inherited from `ubuntu-latest`, no explicit setup-node | Pin an owner-approved supported Node line in a dedicated toolchain change |
| Browser compatibility shim | `run-viewport-qa.py` and `inclusive-qa.py` call gcc/Linux `/tmp/stublibs` setup unconditionally; resilience runner gates on REPL_ID | Gate the shim to the actual Replit/Nix need, and fail with a clear unsupported-runtime message elsewhere; add Windows/Linux tests before changing |
| Mermaid | Vendored `VERSION` 11.17.2 and license included in artifact | Retain exact vendored provenance; review upstream changes and refresh audit before upgrade |
| Dependabot | Monthly grouped Actions/npm; one open grouped PR; no pip ecosystem | Add Python coverage only with the chosen requirements format and review policy |

Evidence status: the exact action and package candidates below were VERIFIED
earlier in this session through individual upstream reads. The later machine
refresh in [platform-inventory.json](../../assets/audit/remaining-program-2026-09-05/platform-inventory.json)
records **INVENTORY REFRESH FAILED** for every GitHub/PyPI request because network
access was denied; only its local source/runtime inventory succeeded. The retry
stopped at an approval/tool wait and was aborted, so no successful refreshed
inventory exists. Do not cite that file as verification of the candidate pins.
The prior individual tool responses were not exported into a successful raw
inventory file. Re-verification is pending before adopting any candidate; no
additional remote call is part of this handoff correction.

Version provenance: [Playwright on PyPI](https://pypi.org/project/playwright/),
[BeautifulSoup4 on PyPI](https://pypi.org/project/beautifulsoup4/), and checked-in
`package.json` / `package-lock.json`. Observed candidate wheel hashes are
Playwright Windows AMD64 SHA-256
`92c0d98ed04eb35af557b709875edba415b1f548bdb22ddb5bb3e1e6c835c2f1`
and BeautifulSoup4 wheel SHA-256
`d6f88de62e1d4e38ecb1077eb9724cd0eff29d2a08ca16a401e9b9e93f117cf9`.
These are provenance examples, not a complete multi-platform hash lock or an
assertion that these uninstalled candidate versions pass this project.

All seven workflows currently follow `check-workflow-actions.py`'s approved
major-tag policy. Full-SHA action references currently fail that checker.
GitHub recommends full commit SHAs for immutable action references; adopt that
only together with the checker, regression cases, readable version comments,
Dependabot configuration, and reviewed upstream provenance.
[GitHub Actions secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use)

September 5 read-only upstream tag resolution (candidate pins, not adopted):

| Action tag | Commit |
|---|---|
| `actions/checkout@v7` | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/setup-python@v7` | `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| `actions/upload-artifact@v7` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |
| `actions/download-artifact@v8` | `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` |
| `actions/configure-pages@v6` | `45bfe0192ca1faeb007ade9deae92b16b8254a0d` |
| `actions/upload-pages-artifact@v5` | `fc324d3547104276b827a68afc52ff2a11cc49c9` |
| `actions/deploy-pages@v5` | `368f82528645a54fb793d4d04e342629a3f51346` |
| `actions/github-script@v9` | `3a2844b7e9c422d3c10d287c895573f7108da1b3` |

The last reference is an annotated tag: tag object
`373c709c69115d41ff229c7e5df9f8788daa9553` was dereferenced to its commit.
Resolution used GitHub's `repos/actions/<name>/git/ref/tags/vN` API and, for
that object, `git/tags/<sha>`. A resolved SHA proves provenance at observation,
not a security review or future tag stability. Re-resolve and review before use.

## Host-header decision

The current source has enforcing per-page meta CSP. GitHub Pages does not apply
the repository's `_headers` file. Framing restrictions and other HTTP-only
controls are not established by a successful source CSP test or meta policy.
The existing live header job is nonblocking; a missing-header result is a
limitation, not protection PASS. No live deployment was changed here.

| Owner choice | Concrete implementation boundary | Acceptance and rollback |
|---|---|---|
| A: Retain GitHub Pages | Keep current domain/publishing and explicitly accept remaining HTTP-header limitations | Recheck live headers and document absent controls; no new protection claim |
| B: Keep Pages origin, add approved Cloudflare proxy | Owner selects account/zone/plan, exact hostname, DNS/proxy/certificate ownership and Response Header Transform Rules | Test origin routing, HTTPS, error responses, CSP and arcade iframe on an approved preview; preserve previous DNS/rule state for rollback |
| C: Move artifact delivery to Cloudflare Pages or Netlify | Owner chooses provider/project, deploy credentials, domain cutover, workflow changes and rollback to Pages; serve the same verified inventory | Preview the actual artifact, confirm paths/provenance/headers on success and error responses, then authorized DNS cutover and live acceptance |

Primary implementation references: [Cloudflare Pages headers](https://developers.cloudflare.com/pages/configuration/headers/),
[Cloudflare response-header rules](https://developers.cloudflare.com/rules/transform/response-header-modification/),
[Netlify custom headers](https://docs.netlify.com/manage/routing/headers/).
Provider syntax and scope differ, so `_headers` must be reviewed for the chosen
host rather than assumed portable without changes.

Before B/C, the owner must choose permitted embedding parents (`frame-ancestors
'self'` versus explicit partners), compatible X-Frame-Options, analytics
allowlist, COOP/CORP behavior with the external arcade iframe, and HSTS coverage.
The source's `includeSubDomains; preload` must not be imposed until all affected
subdomains and rollback implications are reviewed. Review the union HTTP CSP
alongside each narrower meta CSP; both policies apply. Replace blanket immutable
caching for mutable names such as app.js/adapter scripts with a reviewed policy.
A reporting endpoint is another explicit owner choice; none currently exists.

## R13: Analytics retention and field evidence

Confirmed source policy in `legal/index.html` and `docs/threat-model.md`: optional
analytics is off by default, uses explicit browser consent, and is configured
without Google signals, ad-personalization signals, or GA4 client-side storage.
The owner policy target is analytics property retention of **14 months or less**.
The provider-side retention setting is **unverified**. A stored consent choice,
source tag configuration, blocked-request browser test, or passing reload test
does not prove provider retention, ingestion, deletion, or field performance.

Minimal owner-evidence checklist, with no settings changed by this task:

- [ ] Identify the intended GA property and web stream; privately compare the
  measurement identifier to the site's configured identifier.
- [ ] Record the date, reviewer, configured event/user data-retention duration,
  and any reset-on-new-activity setting from that property's administration UI.
  Redact account/access details from public evidence.
- [ ] Confirm the observed duration meets the 14-month-or-less owner target;
  record any exception or proposed change for explicit owner decision.
- [ ] Check relevant sharing, signals, linked advertising/export destinations,
  and who can access retained data. Source flags alone do not certify those
  provider controls or separately retained exports.
- [ ] Record a follow-up review date and evidence owner. Update the operational
  statement only after verification; do not claim historic deletion merely
  because a current setting was observed.

Proposal coordinated with the Experience Worker: run moderated sessions with
five or six consenting participants, including at least two primary keyboard
users and a desktop/mobile mix. Ask them to find a suitable tool, interpret an
unavailable state and find an alternative, search for a seniority or scheduling
need, and explain the external handoff/access boundary before opening it.
Record completion without help, incorrect unavailable-launch attempts (target
zero), status comprehension, next-step confidence, assistance, and errors.
Task time is descriptive, not a population performance estimate. Compare the
current and proposed search layout in counterbalanced order using the same
prompts. Collect no credentials or personal queries and no recordings by default.

This proposal adds no site events, trackers, session replay, or analytics
instrumentation. Obtain separate participant consent, agree a short retention
period before collection, keep only deidentified task tallies/notes, and delete
raw notes at that agreed date. The owner selects the recruitment, evidence
custodian, and retention duration. Local lab measurements do not establish field
INP, real-user p75, production font delivery, or a representative usability rate.

## Executable local release handoff

The PM integrates content and runtime changes, runs generators in the documented
order, reviews their diff, and commits the final source. This worker does not
regenerate or commit. Run the following from a **clean final checkout**; halt
on any nonzero result. Runtime paths below describe this machine only.

```powershell
$releasePython = 'C:/Users/jamie/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$releaseNode = 'C:/Users/jamie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NODE_PATH = 'C:/Users/jamie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$releaseSha = (git rev-parse HEAD).Trim()
if (git status --porcelain) { throw 'Review and commit the final tree before release evidence.' }
git diff --check
if ($LASTEXITCODE) { throw 'Whitespace check failed.' }
$releaseChecks = @(
  @('scripts/build-search-index.py', '--check'),
  @('scripts/sync-portfolio-stats.py', '--check'),
  @('scripts/sync-social-card.py', '--check'),
  @('scripts/sync-css-version.py', '--check'),
  @('scripts/check-links.py', '--no-report'),
  @('scripts/check-csp.py'),
  @('scripts/check-glee-dark-coverage.py', '--section', 'all', '--require-both'),
  @('scripts/check-workflow-actions.py'),
  @('scripts/check-catalog-claims.py'),
  @('scripts/tests/test_content_claims.py'),
  @('scripts/tests/test_public_artifact.py')
)
foreach ($releaseCheck in $releaseChecks) {
  & $releasePython @releaseCheck
  if ($LASTEXITCODE) { throw "Release check failed: $releaseCheck" }
}
# These three checks always write reports and need tracked-file Git metadata.
# Use an isolated local clone; report side effects remain in that evidence copy.
$releaseSource = (git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE) { throw 'Source repository lookup failed.' }
$releaseEvidence = Join-Path $env:TEMP ('glee-checks-' + [guid]::NewGuid().ToString())
git clone --no-hardlinks --no-checkout -- $releaseSource $releaseEvidence
if ($LASTEXITCODE) { throw 'Local evidence clone failed.' }
git -C $releaseEvidence checkout --detach $releaseSha
if ($LASTEXITCODE) { throw 'Exact release checkout failed.' }
$releaseEvidenceSha = (git -C $releaseEvidence rev-parse HEAD).Trim()
if ($LASTEXITCODE -or $releaseEvidenceSha -ne $releaseSha) { throw 'Evidence clone SHA mismatch.' }
Push-Location $releaseEvidence
try {
  foreach ($releaseCheck in @(
    @('scripts/validate-site.py'),
    @('scripts/check-accent-contrast.py', '--strict'),
    @('scripts/resilience-qa.py', '--static-only')
  )) {
    & $releasePython @releaseCheck
    if ($LASTEXITCODE) { throw "Report-writing release check failed: $releaseCheck" }
  }
} finally { Pop-Location }
& $releaseNode --test scripts/tests/test-sw-resilience.cjs
if ($LASTEXITCODE) { throw 'Service-worker regression failed.' }
$env:RELEASE_READINESS_ENGINES = 'chromium,webkit'
$env:RELEASE_READINESS_OUTPUT = Join-Path $env:TEMP "glee-browser-$releaseSha.json"
& $releaseNode scripts/tests/test-release-readiness.cjs
if ($LASTEXITCODE) { throw 'Supplementary browser regression failed.' }
$releaseStage = Join-Path $env:TEMP ('glee-release-' + [guid]::NewGuid().ToString())
& $releasePython scripts/public-artifact.py stage --output $releaseStage --commit $releaseSha
if ($LASTEXITCODE) { throw 'Artifact staging failed.' }
& $releasePython scripts/public-artifact.py verify --output $releaseStage --commit $releaseSha
if ($LASTEXITCODE) { throw 'Artifact verification failed.' }
$releaseTar = Join-Path $env:TEMP ('glee-release-' + [guid]::NewGuid().ToString() + '.tar')
tar -cf $releaseTar -C $releaseStage .
if ($LASTEXITCODE) { throw 'Local archive creation failed.' }
& $releasePython scripts/public-artifact.py verify-tar --output $releaseStage --commit $releaseSha --archive $releaseTar
if ($LASTEXITCODE) { throw 'Archive verification failed.' }
```

This local tar round trip is not a GitHub Actions transfer. Keep its output paths
as evidence; never clean unrelated temporary directories. Full release checks
also include all existing workflow jobs, static CSP/dark/contrast gates and the
Python browser runners in their supported environment. A local subset cannot
replace them.

Side-effect correction: `check-links.py --no-report` is an accepted flag;
`validate-site.py --no-report` is **not** supported and is silently ignored.
The earlier local validator pass remains valid as a result, but the earlier
no-write interpretation was incorrect. Validator, strict accent, and resilience
static mode write fixed reports; the local-clone block above confines those
writes outside the source checkout. Advisory audit tools may also write reports
and are not covered by a blanket no-writes claim. Python child tests require
`PYTHONUTF8=1` on this Windows runtime. These final commands are a handoff, not
a claim that every command in the revised block was executed by this worker.
An earlier plain-archive recipe was invalid because CSP page discovery calls
`git ls-files`; absent Git metadata made validation fail with exit 128 even
after reporting 63 HTML pages without issues. The replacement clones only the
existing local repository, retains independent Git metadata/objects, and checks
out the exact release SHA. It performs no remote fetch or dependency install.

Required artifact assertions: 63 validator-scoped HTML pages; 60 search entries
and sitemap URLs; 42 Tool-ette states (1 live, 24 beta, 17 unavailable) unless an
explicit publication decision changes them; exact source bytes and source SHA
in `release-provenance.json`; `CNAME` exactly `glee-fully.tools`; root `.nojekyll`;
`.well-known/security.txt`; approved JSON/runtime/image files and vendor license
and version. Reject development HTML, templates, docs, agent/skill packages,
scripts/config/secrets, unexpected hidden files, links/reparse points, path
escapes, duplicate/unexpected archive entries, or changed/missing bytes. The
validator is the executable inventory authority; these words do not widen it.

## Acceptance checklist and pending categories

- [ ] Final integrated commit is reviewed, clean, and matches the local evidence.
- [ ] All existing source/generator checks and focused regressions pass.
- [ ] Python Chromium/Firefox/WebKit and complete viewport/inclusive/resilience
  workflows pass at that commit; local Firefox runtime failure remains NOT RUN.
- [ ] Owner decides whether remote review settings and required resilience check
  should match the documented policy; actual settings are re-read.
- [ ] Authorization to push/create PR/merge is supplied; local `pr-draft.md` is
  updated for the actual final diff and attached evidence.
- [ ] **CI pending:** exact PR/head and merge commit jobs, not historical green.
- [ ] **Transfer pending:** actual upload/download preserves the same allowlist,
  hidden security file, bytes, SHA and final Pages tar; no repair during deploy.
- [ ] **Deployment pending:** authorized successful deployment for the selected SHA.
- [ ] **Live pending:** public provenance SHA, home/branch/detail/search/legal,
  offline warm recovery, direct SVG, all public hidden files, and forbidden paths
  checked against the deployed artifact. Confirm third-party font/analytics and
  external game behavior separately from blocked-request local fixtures.
- [ ] **Host decision pending:** absent HTTP headers are recorded honestly; B/C
  migration choices above require their own source review and authorization.
- [ ] **Promotion pending:** exact final source/preimage manifests, sibling owner
  approval, isolated target changes and validation; no timestamp-based copying.
- [ ] **Dependency policy pending:** select and test requirements/runtime/action
  policy as a separate reviewable change; this wave installs or upgrades nothing.

After an authorized deployment, `scripts/check-public-headers.py --url
https://glee-fully.tools/` provides header-presence evidence only. Inspect actual
header values and both successful/error responses too. Presence is not proof of
policy correctness; a green deployment does not prove current public SHA.
