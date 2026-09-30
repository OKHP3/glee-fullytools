#!/usr/bin/env python3
"""Synchronize the public transition disclosures without changing catalog states."""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from public_inventory import collect_indexable_html_files, derive_url

ROOT = Path(__file__).resolve().parent.parent
SUPPORTING = {"/", "/about/", "/contact/", "/ecosystem/", "/foundry/",
              "/legal/", "/persona/", "/showcase/", "/universe/"}


def block(name: str, content: str) -> str:
    return f"<!-- AUTOGEN:{name} -->\n{content}\n<!-- /AUTOGEN:{name} -->"


def replace_block(source: str, name: str, content: str, anchor: str) -> str:
    pattern = re.compile(rf"<!-- AUTOGEN:{name} -->.*?<!-- /AUTOGEN:{name} -->", re.S)
    generated = block(name, content)
    if pattern.search(source):
        return pattern.sub(lambda _: generated, source)
    if anchor not in source:
        raise ValueError(f"Missing insertion point for {name}")
    return source.replace(anchor, anchor + "\n" + generated, 1)


def synchronize(source: str, url: str) -> str:
    affected = url.startswith("/toolbox/") or url in SUPPORTING
    catalog = url.startswith("/toolbox/")
    leaf = catalog and len(url.strip("/").split("/")) == 3
    heading = re.search(r"<h1\b[^>]*>(.*?)</h1>", source, re.S)
    name = html.unescape(re.sub(r"<[^>]+>", "", heading[1])).strip() if heading else "this tool"
    context = (f"{html.escape(name)} is part of our original Custom GPT catalog. "
               if leaf else "Our original Custom GPT catalog is entering a new chapter. ")
    if affected:
        notice = f'''<aside class="glee-transition-notice container" aria-labelledby="transition-notice-title">
  <p class="eyebrow">Platform transition underway</p>
  <h2 id="transition-notice-title">The ideas are staying. The platform is changing.</h2>
  <p>{context}OpenAI has scheduled Custom GPT retirement for December 11, 2026. I am actively working to preserve and replatform these concepts as reusable Agent Skills and plugins.</p>
  <p class="glee-transition-detail">A catalog listing or an existing GPT link does not mean a replacement is ready. Each replacement will be reviewed and tested before its new destination is shared.</p>
  <div class="glee-transition-actions"><a href="/next-chapter/">Read about the next chapter</a><button type="button" class="glee-transition-reopen" data-transition-open hidden>Show transition notice</button></div>
</aside>'''
        main_tag = re.search(r'<main\b[^>]*\bid="main"[^>]*>', source)
        if not main_tag:
            raise ValueError(f"Missing main landmark: {url}")
        source = replace_block(source, "GPT-TRANSITION-NOTICE", notice, main_tag[0])
        auto = "true" if url == "/" or catalog else "false"
        dialog = f'''<dialog class="glee-transition-dialog" data-transition-auto="{auto}" aria-labelledby="transition-dialog-title" aria-describedby="transition-dialog-body">
  <div class="glee-transition-dialog-content">
    <p class="eyebrow">A note from Jamie</p>
    <h2 id="transition-dialog-title">A new chapter for Glee-fully</h2>
    <p id="transition-dialog-body">{context}OpenAI has scheduled Custom GPT retirement for December 11, 2026. I am actively working to carry the useful ideas, methods and learning forward into Agent Skills and plugins.</p>
    <p>Building these GPTs taught me a great deal. Their platform is coming to an end, and the work is evolving. Replacements are in development; this notice does not announce a finished migration.</p>
    <div class="glee-transition-actions"><a class="btn btn-primary" href="/next-chapter/">Explore the next chapter</a><button type="button" class="btn btn-secondary" data-transition-close autofocus>Continue browsing</button></div>
  </div>
</dialog>'''
        source = replace_block(source, "GPT-TRANSITION-DIALOG", dialog, "</main>")
    footer = '<li><a href="/next-chapter/">Our next chapter</a></li>'
    # Keep the disclosure reachable from every indexed page, including Arcade and Search.
    footer_section = source[source.index('<footer'):]
    search_link = re.search(r'<li>\s*<a\b[^>]*href="/?search/"[^>]*>.*?</a>\s*</li>', footer_section, re.S)
    if not search_link:
        search_link = re.search(r'<li>\s*<a\b[^>]*>.*?</a>\s*</li>', footer_section, re.S)
    if not search_link:
        raise ValueError(f"Missing footer navigation: {url}")
    source = replace_block(source, "GPT-TRANSITION-LINK", footer, search_link[0])
    source = source.replace("Smart design made human - a joyful suite of custom GPT Tools built with heart.",
                            "Smart design made human. Personalizable tools built with heart, growing beyond Custom GPTs.")
    source = source.replace("Smart design made human \u2014 a joyful suite of custom GPT Tools built with heart.",
                            "Smart design made human. Personalizable tools built with heart, growing beyond Custom GPTs.")
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = []
    pending = []
    for path in collect_indexable_html_files(ROOT):
        source = path.read_text(encoding="utf-8")
        result = synchronize(source, derive_url(path, ROOT))
        if result != source:
            changed.append(str(path.relative_to(ROOT)))
            pending.append((path, result))
    if not args.check:
        for path, result in pending:
            path.write_text(result, encoding="utf-8", newline="\n")
    print(f"Transition disclosures: {len(changed)} {'stale' if args.check else 'updated'} pages")
    return int(args.check and bool(changed))


if __name__ == "__main__":
    raise SystemExit(main())
