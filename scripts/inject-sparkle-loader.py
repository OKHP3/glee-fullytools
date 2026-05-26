#!/usr/bin/env python3
"""
inject-sparkle-loader.py
On every page that contains the site-specials sparkle banner:
  1. Adds data-sparkle-link attribute to the .site-specials-link anchor.
  2. Adds <script src="/assets/js/sparkle-loader.js" defer></script>
     immediately before the closing </body> tag (or before existing scripts).
Idempotent — skips pages already wired up.
Run from repo root.
"""
import re
from pathlib import Path

SKIP = {'assets/', 'attached_assets/', '.local/'}

LINK_RE = re.compile(
    r'(<a\s[^>]*class="[^"]*site-specials-link[^"]*"[^>]*)(>)',
    re.IGNORECASE | re.DOTALL
)
SCRIPT_TAG = '<script src="/assets/js/sparkle-loader.js" defer></script>'

pages = [p for p in Path('.').rglob('*.html')
         if not any(s in str(p) for s in SKIP)]

updated = 0
for page in sorted(pages):
    content = page.read_text(encoding='utf-8', errors='replace')

    # Only process pages that have the sparkle banner
    if 'site-specials-link' not in content:
        continue

    changed = False

    # 1. Add data-sparkle-link to the anchor if not already present
    if 'data-sparkle-link' not in content:
        def add_attr(m):
            return m.group(1) + ' data-sparkle-link' + m.group(2)
        new_content = LINK_RE.sub(add_attr, content, count=1)
        if new_content != content:
            content = new_content
            changed = True

    # 2. Add sparkle-loader.js script tag before </body> if not already there
    if 'sparkle-loader.js' not in content:
        content = content.replace('</body>', SCRIPT_TAG + '\n  </body>', 1)
        changed = True

    if changed:
        page.write_text(content, encoding='utf-8')
        updated += 1
        print(f"  wired: {page}")

print(f"\nSparkle loader injected into: {updated} pages")
