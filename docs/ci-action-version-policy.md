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