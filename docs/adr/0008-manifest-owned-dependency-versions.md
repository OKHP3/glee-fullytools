# ADR-0008: Manifest-owned dependency versions and recurring release review

## Status

Accepted for this local implementation; GitHub activation awaits merge.
Supersedes ADR-0007's duplicate package-version literals only.

## Date

2026-09-18

## Context

The owner requested a complete technology/version inventory, current stable
release research, and a recurring update mechanism. Dependabot already opens
PRs, but the stack checker rejects package versions differing from a second
hard-coded list. Node dependencies also lacked their own pre-merge browser job.

## Decision

Keep exact package versions in package.json, package-lock.json, and
requirements-qa.txt. Check required packages, stable exact pins, and npm
manifest/lock agreement. Retain the existing Node runtime and action-major
policies, safety checks, and nondestructive repair boundaries.

Check packages weekly with grouped Dependabot PRs. Add a read-only weekly
publisher-release report covering declared/locked packages, runtime selectors,
actions, and vendored Mermaid. Preserve the daily Mermaid issue watch. Add
Node dependency/browser validation on PRs. Fail incomplete upstream checks
explicitly; never treat network failure as evidence of currency.

## Consequences

Ordinary package updates can pass policy checks without editing Python version
literals. Passing policy is not compatibility approval: normal PR and release
tests still apply. Runtime upgrades, action major changes, and Mermaid
re-vendoring require coordinated reviewed changes. No automatic merge,
publication, secret, new package dependency, or hosted-setting change is added.

The inventory cannot recover unknown historical runner versions or reconstruct
an absent vendor SBOM. Those limitations and the upgrade order are recorded
in ../technology-update-plan.md.
