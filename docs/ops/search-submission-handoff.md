# Search Submission Handoff

Task: prepare the public sitemap submission handoff for `glee-fully.tools`.
This note records only the verified local prerequisites and the owner action
sequence. It does not claim Search Console, Bing Webmaster Tools, or any
indexing outcome.

## Exact sitemap URL

`https://glee-fully.tools/sitemap.xml`

## Verified local prerequisites

- `CNAME` is set to `glee-fully.tools`.
- `robots.txt` includes a sitemap reference to `https://glee-fully.tools/sitemap.xml`.
- `sitemap.xml` is present at the site root and uses the canonical production
  domain in every listed URL.
- The public site contract still treats the repository root as the publish
  source, with GitHub Pages as the deployment target.

## Bounded preflight

Before any owner submission, confirm the following from the public site:

1. `https://glee-fully.tools/sitemap.xml` returns the XML sitemap without a
   login wall, redirect chain, or host mismatch.
2. `https://glee-fully.tools/robots.txt` is reachable and still advertises the
   sitemap URL.
3. The submitted URL string matches the canonical sitemap URL exactly.

That is the only preflight this handoff can verify locally. It does not prove
ownership, property access, crawlability inside Google or Bing, or indexing.

## Owner action sequence

1. Open Google Search Console for the verified `glee-fully.tools` property.
2. Use the Sitemaps report and submit `https://glee-fully.tools/sitemap.xml`.
3. Check the sitemap status later in the same report and review any fetch or
   parse error before retrying.
4. Open Bing Webmaster Tools for the verified `glee-fully.tools` site.
5. Submit `https://glee-fully.tools/sitemap.xml` in the Sitemaps tool, or rely
   on the `robots.txt` reference if the owner prefers discovery-only handling.
6. Recheck Bing processing status after submission and only treat success as a
   crawl signal, not a ranking guarantee.

## Source notes

- Local source: [`CNAME`](../../CNAME)
- Local source: [`robots.txt`](../../robots.txt)
- Local source: [`sitemap.xml`](../../sitemap.xml)
- Local source: [`docs/deployment.md`](../../docs/deployment.md)
- Local source: [`docs/roadmap.md`](../../docs/roadmap.md)
- Google official guidance: [Sitemaps report](https://support.google.com/webmasters/answer/7451001?hl=en)
- Google official guidance: [Top tasks for Search Console users](https://support.google.com/webmasters/answer/10351509?hl=en)
- Bing official guidance: [Sitemaps](https://www.bing.com/webmasters/help/sitemaps-3b5cf6ed)
- Bing official guidance: [Add and verify site](https://www.bing.com/webmasters/help/add-and-verify-site-12184f8b)
- Bing official guidance: [Getting Started Checklist](https://www.bing.com/webmasters/help/getting-started-checklist-66a806de)

## Limitation

This handoff is intentionally narrow. It confirms the sitemap URL and the
owner-facing submission path, but it does not include account access, live
submission status, or any claim that search engines have indexed the site.

## FoundRy regression execution boundary

The two FoundRy regressions introduced with this handoff run standalone:

```bash
python3 scripts/tests/test-foundry-page.py
python3 scripts/tests/test-foundry-universe-links.py
```

They are not wired into CI in this change because the reserved CI workflow scope
belongs to website PR #32. A follow-up should add an explicit regression step
after that ownership is reconciled; until then, passing site CI does not claim
these two standalone tests ran.
