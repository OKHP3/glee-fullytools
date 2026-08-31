# Contributing

Thanks for your interest in **Glee-fully Tools**.

This repository contains public website source, brand artifacts, and supporting
materials for the Glee-fully Tools suite of personal-utility Custom GPTs.

## Helpful contributions
- Flagging broken links or missing images
- Identifying rendering issues across browsers or devices
- Suggesting documentation clarifications for the Tools or Toolbox sections
- Proposing cleaner artifact organization for public-facing pages

## Please avoid
- Large unsolicited brand rewrites or tone changes
- Structural changes that break live site continuity
- Adding placeholder or experimental content to public-facing pages without
  alignment
- Modifying Tool-ette descriptions without context -- these are carefully
  documented demonstrations

## How to contribute
1. Be specific about the file, page, or artifact in question.
2. Describe the problem first, then the proposed improvement.
3. Keep suggestions practical, respectful, and public-artifact focused.

## Release and review policy

Normal releases go through a pull request into `main`; direct pushes are
reserved for an owner-approved emergency. The required checks, code-owner
coverage, Dependabot cadence, and current GitHub branch-protection status are
recorded in [`docs/release-governance.md`](docs/release-governance.md).

Until the owner-side `main` protection rule is enabled, CODEOWNERS provides
review routing but does not prevent direct pushes. Do not describe the Pages
deployment as approval-protected before that setting is verified.

## Validation before you commit

Run the repository release checks before opening a pull request:

```bash
python3 scripts/build-search-index.py --check
python3 scripts/sync-portfolio-stats.py --check
python3 scripts/sync-css-version.py --check
python3 scripts/sync-social-card.py --check
python3 scripts/validate-site.py
python3 scripts/check-links.py
python3 scripts/audit-site.py --quiet
python3 scripts/check-accent-contrast.py --strict
python3 scripts/check-glee-dark-coverage.py --section all --require-both
```

The PR checks must pass before a merge is acceptable. Browser viewport and
Sparkle QA also run in their dedicated workflows when their paths change.

## Maintainer
Jamie Hill / Glee-fully Tools · OverKill Hill P³™
contact@glee-fully.tools
