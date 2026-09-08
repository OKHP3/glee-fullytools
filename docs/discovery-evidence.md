# Discovery and ownership evidence

**Review date:** 2026-09-07  
**Scope:** repository-side discovery configuration and owner-controlled search setup  
**Status:** repository implementation complete; owner-side console actions pending

## Repository-side evidence

The discovery outputs share one checked-in scope contract:
[`config/public-inventory.json`](../config/public-inventory.json). It defines the
HTML boundary, indexable exclusions, catalog URL shapes, feed membership, and
sitemap metadata. These commands consume that contract:

```bash
python3 scripts/build-search-index.py --check
python3 scripts/generate-sitemap.py --check
python3 scripts/generate-feed.py --check
python3 scripts/sync-portfolio-stats.py --check
python3 scripts/check-links.py
```

The repository can prove that the generated search index, sitemap, feed, and
showcase statistics agree with the checked-in site. It cannot prove that a
search engine has crawled, accepted, or ranked those URLs.

## Search-console owner actions

| Console | Ownership verification | Sitemap submission | Repository status |
|---|---|---|---|
| Google Search Console | Owner must complete verification for `glee-fully.tools` using a console-supported method. | Submit `https://glee-fully.tools/sitemap.xml` after verification. | Not verifiable from this repository; no credential or token is stored here. |
| Bing Webmaster Tools | Owner must complete verification for `glee-fully.tools` using a console-supported method. | Submit `https://glee-fully.tools/sitemap.xml` after verification. | Not verifiable from this repository; no credential or token is stored here. |

When complete, record only the following non-secret evidence in this file:

- console name and verified property/domain;
- date of verification and sitemap submission;
- the console's resulting status label or screenshot reference;
- reviewer initials or owner confirmation.

Never commit verification tokens, HTML token files, API keys, cookies, or
screenshots containing account details. This record intentionally does not claim
verification or submission until the owner supplies that evidence.

## Organization identities

The homepage Organization JSON-LD currently publishes these seven identities:

- `https://overkillhill.com/`
- `https://askjamie.bot/`
- `https://www.linkedin.com/company/overkillhillp3`
- `https://facebook.com/OverKillHillP3/`
- `https://x.com/OverKillHillP3`
- `https://www.youtube.com/@Glee-fullyTools`
- `https://ko-fi.com/gleefullypersonalizabletools`

These URLs were already present in the public structured data and are retained
without adding any new social identity. Repository inspection does not contain
separate owner approval evidence for them, so their publication is recorded as
**owner confirmation required**, not as a newly verified fact. Remove or amend
an identity if the owner says it is not an official property.