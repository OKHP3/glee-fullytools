# Technology inventory and update plan

Review date: September 18, 2026, America/Chicago (September 19 UTC).
Scope: this Glee-fullyTools repository, including deployment and QA. Initial
baseline: `10f6b580bfe53b4c836297ee69641a509ab714c0`. The current register was
refreshed against integration commit `b0fcafb16a070a99c33c947b77ea6edfdf0c158d`.

Reconciliation follow-up (September 19 UTC): the integration branch also
includes the seven previously unpublished Replit commits and the pending
Mermaid 12.0.0 update from PR #46. All 106 committed Mermaid runtime/license
files match the publisher's npm tarball. The current register and tables below
include Mermaid 12.0.0. The September 18 JSON remains as historical evidence.
Hosted checks and release acceptance belong to the
integration PR and its exact merged commit, not the initial local audit.

## Findings

The delivered website uses HTML, CSS, native JavaScript, browser APIs, and a
vendored Mermaid renderer. Python maintains and tests the site. Node.js runs
QA tools. There is no application server, bundler, database, or framework.
TypeScript, Vite, Tailwind, React, and Next.js are not application dependencies.
Mentions in imported skills, historical documentation, or a dependency's source
maps do not establish an application dependency.

The [generated version register](technology-version-register.md) lists every
one of the 114 npm lockfile entries, the Python dependencies, runtime selectors,
vendored Mermaid, and all nine GitHub Actions. Each of its 135 records includes
current evidence, a publisher release URL, latest stable release, and result.
The [JSON snapshot](../assets/audit/technology-versions-2026-09-19.json) preserves
the same results, including current-major and LTS Node versions and npm engine
requirements. It is a dated snapshot, not a promise that these remain latest.

| Technology | Repository version | Latest stable found | Treatment |
|---|---|---|---|
| Node.js | 22.19.0; Replit selects 20 | 26.9.0 Current; 24.21.0 LTS | Prefer LTS for the upgrade; 22.23.2 is the latest same-major patch |
| Python | CI and Replit select 3.11; patch floats | 3.14.7 | Test the newer minor before changing every selector |
| npm | Not separately pinned; Node 22.19.0 bundles 10.9.3 | 12.0.2 | Upgrade with a compatible Node version; npm 12 requires a newer Node than the current pin |
| Playwright, npm | 1.60.0 | 1.63.0 | Dependabot PR and Node browser gate |
| Playwright, Python | 1.60.0 | 1.63.0 | Dependabot PR and Python browser gates |
| Puppeteer | 25.10.0 | 25.11.0 | Dependabot PR; retain optional QA use |
| Lighthouse | 13.4.1 | 13.5.0 | Dependabot PR; no production runtime role |
| Beautiful Soup | 4.15.0 | 4.15.0 | Current; retained declared QA dependency |
| Mermaid | 12.0.0 | 12.0.0 | Updated through the reviewed integration of PR #46 |
| actions/setup-node | v4 | 7.0.0 | Update action policy, tests, and all references together |

Version evidence comes from the publisher endpoints linked on each row in the
register. Other actions already select the latest major: checkout v7 (7.0.1),
setup-python v7 (7.0.0), upload-artifact v7 (7.0.1), download-artifact v8
(8.0.1), configure-pages v6 (6.0.0), upload-pages-artifact v5 (5.0.0),
deploy-pages v5 (5.0.1), and github-script v9 (9.0.0). Major tags move; this
does not establish the exact action commit used by an earlier run.

## Browser engines and native helpers

Browsers are coupled to their automation package. Do not independently replace
the browser binaries with whatever is newest and assume the package supports it.

| Component | Selected by current package | Selected by latest package / current stable |
|---|---|---|
| Playwright Chromium and headless shell | 148.0.7778.96, revision 1223 | Playwright 1.63.0: 153.0.8010.12, revision 1243 |
| Playwright Firefox | 150.0.2, revision 1522 | Playwright 1.63.0: 155.0, revision 1543 |
| Playwright WebKit | 26.4, revision 2287; platform overrides exist | Playwright 1.63.0: 26.6, revision 2359; this is a test build, not an installed Safari claim |
| Playwright FFmpeg helper | Revision 1011 | Revision 1011 in 1.63.0 |
| Playwright Windows dependency helper | winldd revision 1007 | Revision 1007 in 1.63.0 |
| Puppeteer Chrome and headless shell | 152.0.7977.75 | Puppeteer 25.11.0: 153.0.8010.36 |
| Puppeteer optional Firefox target | stable_155.0 | Puppeteer 25.11.0: stable_155.0.1 |
| Standalone Chrome for Testing Stable | Not independently pinned | 153.0.8010.52 |
| Standalone Firefox Stable | Not independently pinned | 156.0 |

Sources, retrieved September 19 UTC: Microsoft's [1.60.0 browser manifest](https://raw.githubusercontent.com/microsoft/playwright/v1.60.0/packages/playwright-core/browsers.json)
and [1.63.0 manifest](https://raw.githubusercontent.com/microsoft/playwright/v1.63.0/packages/playwright-core/browsers.json),
Puppeteer's [25.10.0 revisions](https://raw.githubusercontent.com/puppeteer/puppeteer/puppeteer-v25.10.0/packages/puppeteer-core/src/revisions.ts)
and [25.11.0 revisions](https://raw.githubusercontent.com/puppeteer/puppeteer/puppeteer-v25.11.0/packages/puppeteer-core/src/revisions.ts),
Google's [Chrome channel feed](https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json),
and Mozilla's [Firefox release feed](https://product-details.mozilla.org/1.0/firefox_versions.json).
These publisher manifests establish selected versions, not evidence that all
browsers are installed on Windows or Replit.

The Linux viewport runner also contains a small C source string compiled with
GCC into a libgbm compatibility stub. It does not pin a C language edition,
compiler, Mesa implementation, or ABI package version. Its soname is
`libgbm.so.1`. GCC's newest released series is [16.2](https://gcc.gnu.org/);
the runner's actual compiler must be recorded from its job environment.

## Standards, data formats, and provider-managed technology

These are real technology surfaces, but most have no installable version to
increment. A standard's edition is not proof of full site conformance.

| Technology | In-place evidence / version | Current reference and update approach |
|---|---|---|
| HTML | HTML doctype; static pages | [WHATWG Living Standard](https://html.spec.whatwg.org/multipage/); use structural and browser tests |
| CSS | Handwritten theme.css, custom properties, media queries; no edition pin | [CSS Snapshot 2026](https://www.w3.org/TR/css-2026/); module-based standards, not a CSS package upgrade |
| JavaScript / ECMAScript | Native scripts, ESM, no compiler target | [ECMA-262 edition 17, ECMAScript 2026](https://ecma-international.org/publications-and-standards/standards/ecma-262/); preserve tested browser support |
| DOM, Fetch, URL, localStorage, Service Worker, Cache API, Web App Manifest | Browser-provided APIs used by assets/js and sw.js; no package versions | Browser standards and compatibility tests; the service-worker cache token is an application revision |
| JSON, JSON-LD, Schema.org | JSON data and schema.org structured metadata; vocabulary release unpinned | Standards/vocabulary, not npm dependencies; validate data and structured metadata on changes |
| XML, Atom, sitemap | XML declaration 1.0; Atom namespace 2005; sitemap namespace 0.9 | Stable interchange formats; validate generated feed and sitemap |
| YAML | GitHub workflow, Dependabot, brand files; no parser release pin | [YAML 1.2.2](https://yaml.org/spec/1.2.2/); platform parser owns compatibility; Dependabot's version: 2 is its config schema |
| TOML | .replit configuration; no language-version declaration | [TOML 1.1.0](https://toml.io/en/); only use syntax accepted by Replit |
| Markdown | GitHub docs and Agent Skills | GitHub-managed rendering; no application Markdown engine |
| SVG, PNG, WebP, ICO | Static images and icons; encoder versions mostly unrecorded | File formats, not installed runtimes; preserve source images and test rendering |
| CSP, HTTP headers, HTTPS | Generated CSP, _headers, deployment TLS | Browser and hosting features; run CSP/header/privacy checks after changes |
| Google Fonts | CSS API v2; Fredoka, Open Sans, Poppins, DM Sans | [Google Fonts CSS2 API](https://developers.google.com/fonts/docs/css2); binaries served by Google, exact versions unpinned |
| Google Analytics | GA4 / gtag loaded on consent; no script release pin | Provider-managed; exercise consent and network tests |
| GitHub Actions / Dependabot / Pages | Managed services; action refs listed separately | Provider updates service internals; monitor workflow and deployment results |
| Ubuntu CI image | ubuntu-latest selector | Publisher currently maps it to Ubuntu 24.04; 26.04 is separately available. [Runner image inventory](https://github.com/actions/runner-images/blob/main/README.md). Per-run image revision is unknown here |
| Replit / Nix | web, nodejs-20, python-3.11 modules; stable-25_05 channel | [Replit configuration](https://docs.replit.com/features/project-setup/configuration) governs availability. Upstream [Nix 2.35.2 / NixOS 26.05](https://nixos.org/download/) do not prove Replit supports a matching channel |
| Bash / shell utilities | post-merge.sh, CI shell steps; no repository pin | GNU Bash stable release line 5.3; [publisher announcement](https://lists.nongnu.org/archive/html/bash-announce/2025-07/msg00000.html). Patch level is distributor-managed |
| curl | CI readiness and release requests; no repository pin | [8.22.0](https://curl.se/download.html); prefer maintained runner packages over independent CI installs |

All web references in this section were checked September 19, 2026 UTC. They
are first-party specifications, release feeds, or hosting documentation. Where
no fixed release is offered, the table says so instead of inventing a version.
External GPTs, Ko-fi, social links, Mermaid Theme Builder, FoundRy, and sibling
sites are destinations, not this site's application dependencies. Imported
skill packages are versioned authoring guidance with provenance in skills-lock.json;
their example stacks are not installed here. The active universe-map skill runs
under the same Python toolchain.

## Local and unresolved evidence

The Windows audit host reported Node 24.11.1, npm 11.6.2, and Python
3.14.0rc1. These differ from the repository contract; the Python executable is
a prerelease. Its installed Beautiful Soup is 4.15.0, soupsieve 2.9.2,
typing-extensions 4.16.0, and Pillow 12.3.0. Pillow is used by archived image
conversion tools, is absent from requirements-qa.txt, and matches the latest
[PyPI release](https://pypi.org/pypi/Pillow/json). Local pip is 25.1.1 versus
[26.2.1](https://pypi.org/pypi/pip/json); it is not repository-pinned.

Git for Windows is 2.55.0.windows.5, matching its [latest stable release](https://github.com/git-for-windows/git/releases/latest).
Git Bash reports 5.3.15(2). GitHub CLI is 2.96.0 versus [2.101.0](https://github.com/cli/cli/releases/latest).
These are workstation tools, not application packages. Update them through the
workstation's normal package manager, then repeat environment checks.

Python transitive dependencies are not locked. The register shows latest
soupsieve 2.9.2, typing-extensions 4.16.0, pyee 14.0.0, and greenlet 3.5.6,
but does not claim those are installed in CI. For example, Playwright 1.60.0's
[published metadata](https://pypi.org/pypi/playwright/1.60.0/json) requires
`pyee>=13,<14`; forcing the latest pyee would break that constraint. The
vendored Mermaid bundle contains its own dependencies without a retained
component lock/SBOM. Upgrade that bundle as a unit, preserving its license;
do not claim exact versions of every embedded library from filenames alone.

## Implemented recurring process

1. **Weekly package updates:** `.github/dependabot.yml` checks npm, pip, and
   GitHub Actions each Monday. One grouped PR per ecosystem bounds routine
   churn. Major updates remain visible and require compatibility review.
   Existing branch protections remain authoritative. [Dependabot documentation](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).
2. **Weekly complete register refresh:** `technology-versions.yml` runs Monday
   at 05:17 UTC, or manually. It rediscovers manifests and workflow references,
   queries publisher feeds, and uploads Markdown/JSON results for 30 days.
   Exit 1 flags newer direct versions (Node tracks latest LTS while also
   reporting Current); exit 2 means an upstream check was
   incomplete. A failed fetch never means current. GitHub run notifications
   follow the owner's existing settings.
3. **Daily Mermaid review:** the existing Mermaid Version Watch opens or
   updates its tracking issue. Re-vendoring remains reviewed work.
4. **Usable PR gates:** the stack checker now enforces exact stable package
   pins and npm lock agreement instead of duplicating package versions in
   Python constants. Missing tools, ranges, prereleases, and mismatched locks
   still fail. Runtime and action-major policies remain explicit.
5. **Pre-merge Node evidence:** Site Validation now installs the lockfile,
   checks Puppeteer/Lighthouse load, and runs the existing FoundRy Playwright
   browser test. Existing Python, viewport, resilience, and Pages release
   checks remain in place. Merge only after all applicable checks pass.

This prepares updates; it does not auto-merge or deploy them. The weekly
review reports rather than rewrites runtime selectors, Mermaid assets, or
provider-managed settings. Thus package PR generation is automated, while
the following plan covers the remaining technologies. Schedules become active
only after these files are merged to the default branch. No repository
setting or secret was changed by the inventory implementation. The subsequent
reconciliation publishes the reviewed work through PR #48 and verifies the
merged source, both checkouts, and the Pages deployment separately.
At activation, verify that branch protection requires the new
`Validate Node dependency updates` check if it must block merging. Adding a
job to a workflow does not itself change the repository's required-check list.

Run the same inventory locally with:

```bash
python3 scripts/technology-versions.py --json assets/audit/technology-versions-current.json --markdown docs/technology-version-register.md
```

On Windows, use `py -3` in place of `python3`. Review the dated evidence before
committing refreshed reports. For CI monitoring, append `--fail-on-updates`.

## Upgrade sequence and acceptance criteria

| Order / owner | Action when an update appears | Required acceptance |
|---|---|---|
| 1 / maintainer | Update actions/setup-node v4 to v7 in every workflow, the action allowlist, and policy table together | Action-policy tests and the full PR workflow pass; verify runner compatibility |
| 2 / maintainer | Move Node to 24.21.0 LTS, or first patch 22 to 22.23.2. Update .node-version, package.json engines, package-lock root engines, the checker Node constant, and dependency policy together | npm ci, Node QA, Python QA, and Pages generation under the exact chosen runtime; choose an npm version whose engines match |
| 3 / Dependabot + maintainer | Update Puppeteer, Lighthouse, and both Playwright declarations through PRs; regenerate package-lock with npm, never by hand | Python and Node browser suites pass. Reinstall matching browsers; record any intentional difference between the two Playwright versions |
| 4 / maintainer | Test Python 3.14.7 alongside 3.11, then update every workflow selector and Replit module if supported | All Python regressions, generated files, and Chromium/Firefox/WebKit release tests pass; record installed transitive versions with pip freeze |
| 5 / maintainer | Mermaid 12.0.0 re-vendoring is included in PR #48 from #46; repeat this process for the next release | Verify bundle/version consistency, CSP, both diagram routes, click behavior, light/dark themes, and generated universe interactions |
| 6 / maintainer in Replit | Select supported Node/Python modules and Nix channel; verify actual node, npm, python, shell, compiler, and browser versions | Fresh Replit install and preview pass independently of Windows/CI; do not invent a channel name from upstream NixOS |
| Recurring / maintainer | Review provider notices and standards compatibility monthly; update workstation tools and archived tooling when used | Browser, typography, consent, offline, and deployment smoke checks; record unsupported or deferred changes with a review date |

For every upgrade: inspect the release notes, preserve exact pins, run the
appropriate PR checks, review the diff, merge through protected main, verify
the Pages workflow at the merged SHA, then smoke-test the live site. Revert the
upgrade commit and redeploy the prior validated source if it regresses. An
available release alone is never release acceptance.

## Evidence boundaries and next action

Local verification for this change: 24 focused regression tests passed;
64 production pages validated with zero issues and warnings; 2,829 internal
links checked with zero broken targets; all workflow and Dependabot YAML
parsed; action and stack policy checks passed. The FoundRy browser test passed
14 checks under Node 22.19.0 at 320px and 390px. npm installed the unchanged
lockfile locally, with lifecycle scripts skipped; the CI job uses normal
`npm ci`. Full hosted CI, the complete multi-browser release suite, Replit,
and live deployment were not run for this local maintenance change.

The integration publisher refresh returned 135 records, 10 direct update candidates,
and zero incomplete release lookups. Unpinned current versions remain unknown
as documented above; successful lookup does not fill that evidence gap.

| Claim | Tier | Evidence / consequence if wrong | Next check |
|---|---|---|---|
| Declared and locked versions are inventoried | Confirmed | Repository manifests and generated register; omitted surfaces would evade review | Re-run the inventory after manifest changes |
| Latest package and runtime versions were retrieved | Confirmed as of timestamp | Publisher feeds; stale snapshots could misdirect an upgrade | Scheduled refresh |
| Node 24 LTS is the preferred next runtime | Proposal | LTS recommendation, not a successful migration | Exact-runtime compatibility run |
| Existing CI/Replit actually ran each listed patch version | Unknown | Selectors and local versions cannot establish remote execution | Read fresh job environment logs and Replit output |
| Every vendored Mermaid subcomponent has a known version | Unknown | No retained vendor component lock/SBOM | Capture provenance during re-vendoring |
| New schedules have run on GitHub | Unknown / not activated locally | Workflow source alone is not a hosted run | Merge, dispatch once, and inspect artifacts |

Next action: finish the integration PR's release acceptance, then begin the
remaining runtime and package upgrade PRs above. Mermaid 12.0.0 is included;
the remaining available updates are review candidates, not installed upgrades.
