# GitHub Actions version policy

The workflows under `.github/workflows/` must use the approved major versions
below. The policy is intentionally limited to the action references themselves;
it does not validate workflow triggers, runner images, action inputs, or
third-party action behavior.

| Action | Approved major |
| --- | ---: |
| `actions/checkout` | `v4` |
| `actions/setup-python` | `v5` |
| `actions/upload-artifact` | `v4` |
| `actions/download-artifact` | `v4` |
| `actions/configure-pages` | `v5` |
| `actions/upload-pages-artifact` | `v3` |
| `actions/deploy-pages` | `v4` |

Run the check locally with:

```bash
python3 scripts/check-workflow-actions.py
```

The check runs as part of the main site-validation workflow. A new action or a
deliberate major-version upgrade requires updating both the allowlist in
`scripts/check-workflow-actions.py` and this policy document in the same
change. Pinning to a commit or using an unapproved major tag is rejected so a
workflow cannot silently drift away from the reviewed CI gate.

## Update review cadence

The `Site Validation` workflow runs an action-version review every Monday at
04:17 UTC and can also be started manually. The review calls GitHub's public
release API for each approved action and reports when a newer stable major is
available:

```bash
python3 scripts/check-workflow-actions.py --check-updates
```

The scheduled review is intentionally separate from the normal enforcement
check: it does not automatically change workflow files or the policy. A
reported major is a proposal for maintainer review. If the upgrade is
approved, update the `ACTION_MAJOR_VERSIONS` allowlist, this table, and every
workflow reference in the same change. The existing `python3
scripts/check-workflow-actions.py` step remains the blocking enforcement gate
for pull requests.