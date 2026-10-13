# GitHub Pages public-content policy

The Pages workflow publishes a generated `dist-pages/` directory, not the
repository checkout. The artifact must contain only the public site and the
release provenance record.

## Boundary

The allowlist is defined in `scripts/public_inventory.py` and enforced by
`scripts/check-pages-artifact.py`. The workflow copies the public checkout while
excluding internal, sensitive, and development-only paths, then runs the policy
check **after** adding `release-provenance.json` and before uploading.

The policy rejects:

- repository metadata and automation (`.git/`, `.github/`, `.agents/`, `.local/`,
  `scripts/`, and editor/cache directories);
- package manifests, dependency installs, configuration, and source attachments;
- `docs/`, audit reports, templates, downloads, and other maintainer material;
- any unexpected top-level path;
- a missing `release-provenance.json`.

Public runtime data under `assets/css/`, `assets/data/`, `assets/img/`,
`assets/js/`, and `assets/vendor/` remains allowed. `assets/audit/` and
`assets/docs/` are excluded by the copy policy and rejected if they reappear.

## Local check

The check requires the same provenance file that the workflow injects:

```bash
rm -rf /tmp/pages-policy-fixture
mkdir -p /tmp/pages-policy-fixture
printf '{"commit":"local-check"}\n' > /tmp/pages-policy-fixture/release-provenance.json
python3 scripts/check-pages-artifact.py /tmp/pages-policy-fixture
```

The workflow's actual artifact check is the release evidence. A local fixture
can verify the validator's pass/fail behavior but is not a deployment.

## Validation evidence retention

The separate validation artifact requests 90 days of retention. Before deployment,
the workflow checks its effective expiration using authenticated GitHub artifact
and workflow-run metadata. Both responses must identify the current run and
release commit; missing or mismatched metadata blocks deployment.

GitHub's retention deadline is measured from the original workflow run's
`created_at`, not the later artifact upload or rerun start. The checker requires
at least 90 days from that timestamp, with no tolerance for a shorter period. An
upload made after validation therefore has less than 90 days remaining at upload
time. Artifacts must also be unexpired and have valid creation/expiration order.

The daily retention monitor checks successful Pages runs whose review windows
remain open and whose source includes the first 90-day retention-policy commit,
`edf2d3509e6b51cdd42ad36cd9ca1dd111cfd08e`. GitHub's commit comparison establishes
that ancestry; a release that predates the policy is excluded, while unavailable
or divergent ancestry fails the check. This avoids imposing a new artifact
requirement on older releases that did not promise 90-day retention. The monitor
reads workflow and artifact metadata only; it does not deploy, recreate missing
evidence, or change retention settings.
