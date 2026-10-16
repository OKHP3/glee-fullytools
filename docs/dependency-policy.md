# Dependency reproducibility policy

The project remains a no-build static site, but its validation and browser
checks have dependencies. Reproducibility is governed as follows:

- GitHub Actions use approved major versions checked by
  `scripts/check-workflow-actions.py`.
- Python QA dependencies are exact-pinned in `requirements-qa.txt`; CI installs
  that file rather than an unbounded package name.
- Puppeteer, Lighthouse, and the focused FoundRy Node Playwright runner are
  exact-pinned in `package.json` and represented in `package-lock.json`; CI or
  maintainers use `npm ci` when Node QA is run.
- Node itself is pinned to `22.23.3` by `.node-version` and the package
  `engines` field before running npm tooling.
- The Node Playwright package's pinned version owns the browser revision
  installed by `npx playwright install`; the Python Playwright dependency
  continues to own the existing Python browser gates. Browser installation is
  explicit in browser workflows.
- Dependabot reviews GitHub Actions, npm, and pip updates weekly on Monday. Every update
  remains a reviewed pull request and must pass the normal release checks.
- An update must change the relevant lock/pin file, run the full applicable QA
  suite, and record any intentional compatibility decision in the pull
  request. No floating dependency may be introduced as a convenience.
- Package manifests own dependency versions. The stack checker validates exact
  stable pins and npm lock agreement rather than a duplicate version list.
  Node and GitHub Action major changes still require coordinated policy edits.
- Site Validation installs and exercises Node QA dependencies on pull requests,
  alongside the existing Python/browser gates.
- The weekly Technology Version Review reports newer stable runtime, package,
  action, and Mermaid releases. It never edits pins or merges a PR. See the
  [inventory and upgrade plan](technology-update-plan.md) and
  [generated version register](technology-version-register.md).

Current update path:

```bash
python3 -m pip install -r requirements-qa.txt
npm ci
python3 scripts/check-workflow-actions.py
```

The exact versions are policy, not a claim that dependencies never need
updating. Security and browser compatibility updates should use the weekly
review or an earlier reviewed update when risk warrants it.

## October 16, 2026 bounded update review

The QA package update selects Node Playwright 1.64.1, Python Playwright 1.64.0,
and Puppeteer 25.14.0, with the Node runtime patched within the existing 22.x
line to 22.23.3. npm remains the version bundled with that Node release; it is
not independently upgraded. Exact package pins and the npm lock remain
mandatory. The stack checker uses the same Node pin.

The inventory still compares Node against latest LTS, so a Node 24 migration
can remain a candidate after this patch. Node 24/npm 12 and Python 3.15 are
separate runtime migrations, not required to consume these compatible QA
package releases. Replit module selectors stay unchanged while its shared
workspace may have active work; this branch does not change that environment.

| Candidate | Reviewed disposition |
|---|---|
| npm Playwright 1.64.0 → 1.64.1 | Apply the patch; use its package-owned browser revisions. |
| Puppeteer 25.13.0 → 25.14.0 | Apply within the existing major; retain optional QA tooling. |
| Python Playwright 1.63.0 → 1.64.0 | Apply within the existing major; test all three engines. |
| Node 22.19.0 → latest LTS 24.22.0 | Apply 22.23.3 in the supported existing line; defer the Node 24 migration. |
| Bundled npm 10.9.3 → npm 12.2.0 | Consume bundled npm 10.9.9 with Node 22.23.3; defer a separate npm major. |
| Python CI 3.11 → 3.15 | Retain 3.11 for this package update; a runtime migration needs its own compatibility matrix. |
| Replit Node selector 20 → 24 | Defer shared-workspace runtime changes; current active-work status is unknown. |
| Replit Python selector 3.11 → 3.15 | Defer shared-workspace runtime changes; preserve the existing preview environment. |

Publisher evidence reviewed for this change:
[Playwright 1.64.1](https://github.com/microsoft/playwright/releases/tag/v1.64.1),
[Python Playwright 1.64.0 metadata](https://pypi.org/pypi/playwright/1.64.0/json),
[Puppeteer 25.14.0](https://github.com/puppeteer/puppeteer/releases/tag/puppeteer-v25.14.0),
and [Node 22.23.3 LTS](https://nodejs.org/en/blog/release/v22.23.3).
