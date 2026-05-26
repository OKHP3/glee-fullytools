#!/usr/bin/env python3
"""Fix the 3 placeholder GPT links in tool-ette pages.

Idempotent: skips pages where the real URL is already present.
Real URLs sourced from branch index pages (verified 2026-05-26).
"""
from pathlib import Path
import re

FIXES = [
    {
        "page": "toolbox/02-treasured-finds/02c-present-hoarder/index.html",
        "real_url": "https://chatgpt.com/g/g-685af65a822881919690d7410a122984-present-hoarder-by-glee-fully",
        "placeholder_patterns": [
            r'href="https://chatgpt\.com"\s',
            r'href="https://chatgpt\.com"',
        ],
        "cta_text_old": 'Launch "Present Hoarder" in ChatGPT',
        "cta_text_new": 'Open Present Hoarder in ChatGPT',
        "todo_comment": "<!-- TODO: replace href with the specific Present Hoarder GPT URL once finalized -->",
    },
    {
        "page": "toolbox/04-travelers-guide/04d-dreamland-journeys/index.html",
        "real_url": "https://chatgpt.com/g/g-685b072fccec8191a595b10991348f30-dreamland-journeys-by-glee-fully",
        "placeholder_patterns": [
            r'href="https://chat\.openai\.com/"',
        ],
        "cta_text_old": "Launch Dreamland Journeys",
        "cta_text_new": "Open Dreamland Journeys in ChatGPT",
        "todo_comment": "<!-- TODO: swap href for the live Dreamland Journeys GPT link when ready -->",
    },
    {
        "page": "toolbox/04-travelers-guide/04e-memento-log/index.html",
        "real_url": "https://chatgpt.com/g/g-685b072be58c8191ba386b00b33b93b8-memento-log-by-glee-fully",
        "placeholder_patterns": [
            r'href="https://chatgpt\.com/g/REPLACE_WITH_MEMENTO_LOG_GPT_ID"',
        ],
        "cta_text_old": 'Launch "Memento Log" in ChatGPT',
        "cta_text_new": "Open Memento Log in ChatGPT",
        "todo_comment": "<!-- TODO: replace href with the real GPT URL for Memento Log -->",
    },
]

ROOT = Path(__file__).parent.parent
changed = 0

for fix in FIXES:
    path = ROOT / fix["page"]
    if not path.exists():
        print(f"  SKIP (not found): {fix['page']}")
        continue

    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")

    if fix["real_url"] in text:
        print(f"  SKIP (already fixed): {fix['page']}")
        continue

    original = text

    # Remove TODO comment
    if fix["todo_comment"] in text:
        text = text.replace(fix["todo_comment"], "")

    # Replace placeholder href with real URL (try each pattern)
    for pat in fix["placeholder_patterns"]:
        text = re.sub(pat, f'href="{fix["real_url"]}"', text)

    # Update CTA text if needed
    if fix["cta_text_old"] in text:
        text = text.replace(fix["cta_text_old"], fix["cta_text_new"])

    if text != original:
        path.write_bytes(text.encode("utf-8"))
        print(f"  FIXED: {fix['page']}")
        changed += 1
    else:
        print(f"  WARN: no change made to {fix['page']} — check patterns")

print(f"\nDone. {changed} file(s) updated.")
