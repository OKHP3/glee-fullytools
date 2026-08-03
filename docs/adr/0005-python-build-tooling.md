# ADR-0005: Python-Based Build and Maintenance Tooling

## Status

Accepted

## Date

2025-01-01

## Context

Static HTML pages (ADR-0001) require coordinated maintenance: shared nav and footer
must be consistent, JSON-LD must be valid, search indexes must stay current, and
image pipelines must produce correct WebP variants. This tooling runs at author time,
not in the browser.

## Decision Drivers

- **Author availability**: The project owner is comfortable with Python
- **Standard library sufficient**: HTML parsing, JSON, file I/O — no exotic dependencies
- **CI integration**: GitHub Actions can run Python 3.9+ without special setup
- **Cross-platform**: Works on Windows, macOS, and Linux (the three author environments)

## Considered Options

### Option A: Python scripts (chosen)
- Pure stdlib where possible; `BeautifulSoup` for HTML parsing only where necessary
- All scripts named kebab-case, categorized by purpose

### Option B: Node.js / shell scripts
- **Pros**: Tooling ecosystem matches modern web development
- **Cons**: Adds Node.js dependency, mixes runtimes, unfamiliar to project owner

### Option C: Makefile
- **Cons**: Poor Windows support, harder to maintain script logic

## Decision

All build and maintenance scripts are Python (`.py`) under `scripts/`. Scripts are
categorized as validators, index/feed builders, idempotent mutators, image pipeline,
governance/sync, or QA runners. All filenames are kebab-case.

Scripts that mutate HTML use `<!-- AUTOGEN:<MARKER> -->` comments for idempotency.
Validators exit non-zero on failure for CI use.

## Consequences

### Positive
- Single runtime (Python) for all tooling
- Scripts are readable, maintainable, and testable
- GitHub Actions CI works without special Node.js setup

### Negative
- Scripts directory has grown to 55+ scripts and needs periodic auditing
- Some scripts are one-shot migration tools that are no longer safe to re-run

### Constraints
- Do not add npm/Node.js build steps to the site content pipeline
- Script run-order dependencies must be documented in `AGENTS.md`
- One-shot scripts must be marked with a header comment noting they are not safe to re-run
