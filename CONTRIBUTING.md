# Contributing

Thanks for your interest in **Glee-fully Tools**.

This repository contains public website source, brand artifacts, and supporting
materials for the Glee-fully Tools suite of personal-utility Custom GPTs.

## Helpful contributions
- Flagging broken links or missing images
- Identifying rendering issues across browsers or devices
- Suggesting documentation clarifications for the Tools or Toolbox sections
- Proposing cleaner artifact organization for public-facing pages

## Please avoid
- Large unsolicited brand rewrites or tone changes
- Structural changes that break live site continuity
- Adding placeholder or experimental content to public-facing pages without
  alignment
- Modifying Tool-ette descriptions without context -- these are carefully
  documented demonstrations

## How to contribute
1. Be specific about the file, page, or artifact in question.
2. Describe the problem first, then the proposed improvement.
3. Keep suggestions practical, respectful, and public-artifact focused.

## Validation before you commit

Run the site auditor and rebuild the search index before opening a pull request:

```bash
python3 scripts/audit-site.py
python3 scripts/build-search-index.py
```

Both scripts write output to `assets/docs/`. The auditor must report 0 issues
before a merge is acceptable.

## Maintainer
Jamie Hill / Glee-fully Tools · OverKill Hill P³™
contact@glee-fully.tools
