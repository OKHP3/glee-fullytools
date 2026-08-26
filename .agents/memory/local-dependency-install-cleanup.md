---
name: Local dependency install cleanup
description: Environment behavior to account for when installing temporary Python validation dependencies.
---

A failed environment package install may initialize a uv project and leave untracked helper files in the repository, even when the requested dependency is not installed.

**Why:** The shared Nix Python site-packages directory can be read-only, so a package install may fail after creating project scaffolding.

**How to apply:** After any failed temporary dependency installation, inspect `git status` and remove only clearly installer-generated files before validating the intended change.