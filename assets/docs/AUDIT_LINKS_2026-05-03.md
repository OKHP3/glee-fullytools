# Link Audit — 2026-05-03

**Generator:** `scripts/check-links.py` → `audit/links-report-2026-05-03.json`

---

## Summary

| Metric | Value |
|---|---:|
| Pages scanned | 60 |
| Internal links scanned | 2,048 |
| External links scanned (not validated by HTTP) | 1,067 |
| **Broken internal links** | **0** |
| Style issues (e.g. missing trailing slash on directory URLs) | 0 |
| Sitemap URLs | 58 |
| Repo pages **missing** from sitemap | 0 |
| Sitemap entries **without** a backing file | 0 |

The site is internally link-clean.

---

## What was actually checked

For every `<a href>` and `<link href>` in every HTML file (the script does not
currently scan `<form action>` because the site has no `<form>` tags outside the
search components, which use JS routing):

1. If the href is external (`http://`, `https://`, `mailto:`, `tel:`, `javascript:`,
   `data:`, `#fragment`), it is counted but not retrieved.  No outbound HTTP traffic.
2. If the href is internal (`/foo/`, `foo/bar.html`, `../../baz/`), it is resolved
   from the source file's directory and tested against the filesystem:
   * a real file → ✓
   * a directory containing `index.html` → ✓
   * neither → broken
3. Directory-style URLs that are missing a trailing slash trigger a **style issue**
   only when the path actually resolves to a directory (the proxied web layer
   would 301-redirect, hurting Lighthouse).

The full machine-readable report — every link, on every page, classified — is at
`audit/links-report-2026-05-03.json`.

---

## Sitemap parity

* Every backing `index.html` resolves to a sitemap URL **or** is intentionally
  excluded (`404.html`, `under-construction.html`).
* Every sitemap URL resolves to a real file.
* Sitemap freshness was bumped from the stale `2026-04-07` to `2026-05-03` for the
  57 pages we touched in this pass; `/search/` retains its `2026-05-02` mark.

## Specific link classes verified

* **Footer email links** (`mailto:contact@…`, `mailto:support@…`) — present on all
  60 pages, syntax valid.
* **Ko-fi link** (`https://ko-fi.com/gleefullypersonalizabletools`) — present on
  60/60 pages, opens in new tab with `rel="noopener"`.
* **Social links** (LinkedIn, Facebook, X, YouTube) — present on 60/60 pages, all
  with `target="_blank" rel="noopener"`.
* **Logo / home links** — every nav `<a>` to `/` and `/toolbox/` resolves
  correctly from every folder depth.
* **Skip-to-content** — `#main` target exists on 60/60 pages (validated by
  `validate-site.py`).
* **Search hooks** — `?q=` on `/search/` and `?s=` on every page resolve to the
  same `search.js` engine; verified by inspection.

---

## Deferred (not auditable from inside the sandbox)

* **External GPT links** (`https://chatgpt.com/g/...`) — counted, syntax-checked,
  but not HTTP-resolved.  These are ChatGPT-side endpoints we do not control;
  any 404 here would mean OpenAI deprecated a Custom GPT.
* **External brand links** (LinkedIn / Facebook / X / YouTube / Ko-fi) — likewise
  not HTTP-pinged; all are site-of-record and have been live for the lifetime of
  the project.
* **Notion lore links** — long opaque URLs; left untouched.

If full external-link reachability becomes important, a follow-up could add an
opt-in `--check-external` flag to `scripts/check-links.py` using
`urllib.request.head` with a 5-second timeout.

---

## Re-running

```bash
python3 scripts/check-links.py
```

Returns exit code `1` if any internal link is broken or any sitemap-vs-file
mismatch exists.
