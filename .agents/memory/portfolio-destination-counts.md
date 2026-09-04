---
name: Portfolio destination counts
description: The durable rule for counting configured-looking external destinations in portfolio statistics.
---

Count a Tool-ette as having a configured-looking external destination only when
its intended ChatGPT URL matches the non-placeholder destination pattern. Do not
count every page containing a ChatGPT href: related-tool navigation can contain
valid links even when the page's own launch destination is still a placeholder.

**Why:** Portfolio copy must separate authored catalog coverage from evidence
that a launch destination has been configured, without implying that an
external GPT is reachable or behaviorally verified.

**How to apply:** Keep the portfolio-stat sync and structural validator on the
same conservative destination rule, and label the result as non-placeholder or
configured-looking rather than “live GPTs.”