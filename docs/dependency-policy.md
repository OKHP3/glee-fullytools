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
- Node itself is pinned to `22.19.0` by `.node-version` and the package
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
