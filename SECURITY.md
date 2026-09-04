# Security Policy

This repository contains public website and brand source materials for
Glee-fully Tools.

## Reporting Issues

If you discover:
- exposed credentials
- misconfigured artifacts
- broken links or misleading content

please contact **contact@glee-fully.tools** immediately.

## Scope

No bounty program exists at this time. Reports will be reviewed and mitigated
as practical.

## Notes

This repo is primarily for reference and public brand artifact access.
There is no authentication, first-party database, or contact form. Optional
Google Analytics is off by default and can be enabled from the legal page;
email correspondence and third-party GPT/game interactions are handled by
their respective providers rather than by this static site.

## Release security ownership

Changes to workflows, Pages publishing, `_headers`, runtime JavaScript,
generated runtime data, deployment contracts, and security documentation are
covered by `.github/CODEOWNERS`. That review routing is not the same as active
branch protection; the current GitHub `main` branch rule status and the desired
approval/check policy are recorded in
[`docs/release-governance.md`](docs/release-governance.md).

The `_headers` file is a portable edge-host policy and is not consumed by the
current GitHub Pages host. The live header smoke test in the Pages workflow is
the source of truth for delivered production headers.
