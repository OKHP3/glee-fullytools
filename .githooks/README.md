# Git Hooks

This repository keeps shared Git hooks in `.githooks/`.

Enable them in a local checkout with:

```bash
git config core.hooksPath .githooks
```

The `pre-push` hook blocks direct pushes to `main`. GitHub protects `main` with
pull request review and required checks, so VS Code, GitHub Desktop, Git GUI,
and command-line Git should publish branches and open pull requests instead of
trying to push `main` directly.
