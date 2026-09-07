# Revitalization assignment register

> Historical record. This register is superseded by the reviewed release dispositions in [`docs/remaining-program-2026-09-05/release-dispositions-2026-09-06.md`](../../../docs/remaining-program-2026-09-05/release-dispositions-2026-09-06.md). It is retained for provenance and must not be treated as the current assignment source of truth.

Updated: 2026-09-05. Architect: `01a07281-90d0-7db1-b5db-13c4745fa6b8`.

## Status correction

The assessment and repair designs are complete within their recorded evidence boundaries. Previously, only the first repair wave had an implementation PM assignment. The remaining identified backlog had been documented but not dispatched. The owner's clarification prompted the expanded delegation below. Assignment is not completion, and completed proposals are not implemented features.

## Broad ownership

| PM task | Coverage | Verified dispatch/status |
| --- | --- | --- |
| Revitalization Project Manager | R0, R1, R2, R3, narrow R4, narrow R6, R10, R11; R12 translation-transition followup; R9 visual/interaction proposals | Runnable task `01a07294-4270-7660-8040-9bc5cee80973`. Three Workers dispatched. Runtime and content Worker deliveries reported; PM integration and final rendered visual checks remain active. Expanded ownership and model override accepted by message tool. |
| Release and QA Project Manager | R5 artifact packaging; remaining R6 test coverage/portability; R8 favicon efficiency; INF-05 report provenance/output controls; INF-09 fragment checking/fix; INF-07 CI policy proposal; INF-10 optional Node support proposal | Creation accepted with queued client ID `client-new-thread:abe8a1ab-f984-48c3-8cdb-0a0a17d871b1`. Runnable task identity and Worker execution not yet confirmed at this checkpoint. |
| Catalog and Governance Project Manager | Remaining R4 state/schema contract (C-04/C-08, CD-3); R7/GOV-01/GOV-02 operational guidance and policy reconciliation; C-07/CD-4 evidenced dates and separate feed preview; CD-5 tool proof pilot; R9 discovery/content proposals | Creation accepted with queued client ID `client-new-thread:e7e40af7-5e16-4ce6-947d-3de0330f9f00`. Runnable task identity and Worker execution not yet confirmed at this checkpoint. |

All identified R0-R12 packages and the secondary queue now have an explicit PM owner and submitted scope. R9 is divided by deliverable: the existing PM owns visual/interaction design; Catalog owns discovery copy and proof protocol. Large refactors, changed policy, multilingual launch, feed maintenance decisions and externally supplied evidence remain concrete proposal/decision deliverables. No external behavior or owner decision may be invented to close an item.

## Model and context policy

- Architect retains architectural judgment and final review. PMs use `gpt-5.6-luna` with low reasoning; both new creation requests explicitly set this. The existing PM received the same model override for its next supported turn boundary.
- Narrow documentation and simple implementation Workers should use `gpt-5.4-mini` with low reasoning through task creation when available. The collaboration API does not expose mini; its lightweight supported choice is `gpt-5.6-luna` with low reasoning.
- Coupled runtime/security work may use luna with medium reasoning when the PM identifies a concrete need. Escalation requires a recorded complexity or failure reason. Cheap execution that forces rework is not the objective.
- Pass a self-contained, bounded brief with exact files, evidence and acceptance criteria. Use no inherited full transcript for new collaboration Workers. Reuse a few Workers for related followups rather than creating a large swarm.
- Preserve completed and in-flight work. Do not restart it solely to change models. A requested model policy is not evidence of which model an earlier Worker used; no retrospective cost savings are claimed.

## Integration and completion contract

The existing PM owns first-wave integration in an isolated worktree (path omitted), branch `codex/first-wave-repairs-2026-09-05`, baseline `9b4ade05`. It must provide a verified local commit and changed-file manifest. New PMs can prepare independent documentation, designs and tests, but must coordinate that stable commit before integrating overlapping runtime, HTML, generators or workflow changes. Each works in its own worktree; no PM edits another task's checkout. Source main was observed at `a24d11b3` during this status pass, so each PM must verify its actual base rather than assume the assessment SHA is current.

Workers implement bounded assignments. PMs review diffs, integrate generated artifacts once in the documented order and run meaningful checks on the combined result. Reports must distinguish assignment, implementation, local verification, remote CI and live deployment. The Architect reviews completion evidence across PMs. Final browser checks are still open in the first wave; the first PM's latest task snapshot also reports an approval-wait flag, without a confirmed approval resolution in this record.

Local commits are allowed. Publication, remote merges, repository-setting changes, dependency upgrades, sibling edits and broad refactors remain outside these implementation assignments. This is a reviewable local remediation program; no deployment completion is claimed.

## Catalog PM startup and dispatch correction

Catalog and Governance Project Manager startup is now confirmed as task `01a074b6-7363-7f90-9a61-7f276ba0e02f`, in an isolated detached worktree (path omitted). It produced planning artifacts, but its Worker creation calls failed. Architect inspection found malformed task-creation arguments and attempts to duplicate CD-1/CD-2 already owned by the first wave. The Architect directed it to use a bounded Luna-low collaboration Worker for authorized R7 corrections, supplied the correct alternate task-creation shape, and explicitly prohibited duplicate crawler/copy work. Successful Worker startup remains to be confirmed. These failures are not evidence of an approval denial or completed implementation.

The Catalog PM subsequently confirmed successful R7 Worker dispatch: Carson, agent `01a074b8-ddac-7662-9bbb-dac54c6d0051`, model `gpt-5.6-luna`, low reasoning, limited to the permitted active guidance files. This supersedes the pending Worker-startup status above. CD-1/CD-2 are corrected to external first-wave dependencies. Worker implementation, commit and PM review remain pending.

## September 6 handoff and integration assignment

The first-wave PM delivered tested implementation commit `5410ab11374f8efb8e97ce767be5dd5d654f5653` and documentation-only final HEAD `63b0cb51e0dc2d367b1bec9ae1ad253101a644c6`. The Architect read its implementation report. It records 29/29 static/regression entry points, 1,908 contrast measurements without failures, 11/11 runtime scenarios, 504/504 responsive cases and 12/12 content cases passing on that implementation. This is local Chromium and source evidence, not current-main or deployment proof. The small authorized SVG syntax repair is included.

The Architect verified that the available `origin/main` ref is `4a07fbceab4b669bf304dbbb5e6d429ccd77544e`, containing newer catalog, release and shared-navigation work. The first-wave manifest records 70 overlapping paths. The Architect assigned the same PM a new bounded integration task: use a new isolated worktree, compare findings semantically, retain already-correct upstream changes, apply only proven residual fixes and useful nonduplicate tests, coordinate with other PMs, and verify the final candidate. Preserve the completed handoff branch. No publication is authorized by this assignment.

Luna medium is selected for this PM's coupled integration judgment because of overlapping runtime, generated assets and release contracts. Simple Worker comparisons and documentation retain the low-reasoning model policy. This exception does not authorize restarting completed work or a blanket replay of the 220-file handoff.

Catalog R7 is PM-reviewed at commit `7a074c670481f8d7f59529ec5fd51911766eb720`, with coverage update `3fb40553`; its remaining package matrix has been requested for integration coordination. First-wave local implementation is complete. Current-main integration and the broader program remain open.
