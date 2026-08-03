# Architecture Decision Records — Glee-fully Tools

This directory contains Architecture Decision Records (ADRs) for the Glee-fully Tools website.

ADRs capture the context and rationale behind significant technical decisions. They are written
close to when a decision is made and updated only to change status — never to revise history.

---

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-static-html-no-framework.md) | Static HTML over a Frontend Framework | Accepted | 2025-01-01 |
| [0002](0002-client-side-search-json-index.md) | Client-Side Search with Pre-Built JSON Index | Accepted | 2025-01-01 |
| [0003](0003-cdn-third-party-resources.md) | CDN-Loaded Third-Party Resources | Accepted | 2025-01-01 |
| [0004](0004-enforced-csp-headers.md) | Enforced CSP via _headers File | Accepted | 2026-07-20 |
| [0005](0005-python-build-tooling.md) | Python-Based Build and Maintenance Tooling | Accepted | 2025-01-01 |

---

## Creating a New ADR

1. Copy `template.md` to `NNNN-short-title.md` (e.g. `0006-image-format-choice.md`)
2. Fill in all sections; set Status to `Proposed` until decided
3. Change Status to `Accepted` (or `Rejected`) once the decision is made
4. Add the new ADR to the index table above
5. Update the `docs/` row in `AGENTS.md` section 2.2.1 to reflect the new ADR count

## ADR Status Values

- **Proposed** — Under discussion, not yet decided
- **Accepted** — Decision made and implemented
- **Deprecated** — No longer relevant (context changed)
- **Superseded** — Replaced by a newer ADR (link to it)
