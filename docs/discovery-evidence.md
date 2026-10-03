# Discovery and ownership evidence

**Review date:** 2026-09-29
**Scope:** repository-side discovery configuration and owner-controlled search setup
**Status:** repository implementation complete; owner-side console coverage evidence not supplied

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
python3 scripts/check-search-coverage.py
```

The repository can prove that the generated search index, sitemap, feed, and
showcase statistics agree with the checked-in site. It cannot prove that a
search engine has crawled, accepted, or ranked those URLs.

## Sanitized coverage record

The following record contains only aggregate, non-secret scope metadata. The
checker compares the recorded review date and URL-set digest with the current
`config/public-inventory.json` and `sitemap.xml`; it does not contact either
search console or require console credentials.

```json
{
  "schema": 1,
  "review_date": "2026-09-29",
  "scope": {
    "source": "config/public-inventory.json + sitemap.xml",
    "url_count": 62,
    "url_sha256": "7f58d18a72916f32058e11fa4d5f7c0dab48a3f8d2e76f23bf41bd1493773290"
  },
  "records": {
    "google-search-console": {
      "review_date": "2026-09-29",
      "scope": {
        "url_count": 62,
        "url_sha256": "7f58d18a72916f32058e11fa4d5f7c0dab48a3f8d2e76f23bf41bd1493773290"
      },
      "status": "blocked"
    },
    "bing-webmaster-tools": {
      "review_date": "2026-09-29",
      "scope": {
        "url_count": 62,
        "url_sha256": "7f58d18a72916f32058e11fa4d5f7c0dab48a3f8d2e76f23bf41bd1493773290"
      },
      "status": "blocked"
    }
  }
}
```

## Current repository scope

The September 29 transition update adds `/next-chapter/`, bringing the local
sitemap to 62 URLs. The aggregate scope record above reflects that local review.
Both console statuses remain blocked and their actual indexing counts remain
unknown. No new console verification, submission or crawl result is claimed.

## Historical post-submission coverage review (September 9)

**Review date:** 2026-09-09
**Reviewer:** repository review; no console account details accessed
**Historical coverage scope at the 2026-09-09 review:** 61 unique sitemap URLs:

- 1 homepage
- 1 Toolbox hub
- 7 branch pages
- 42 Tool-ette pages
- 10 supporting pages

At that review, the generated sitemap contained 61 URLs. The current sanitized
coverage record below is scoped to the current 62-URL sitemap. The repository
and public preflight confirm that every sitemap URL has a corresponding public
file, and the live `robots.txt` and
`sitemap.xml` each return HTTP 200 from the canonical host. The repository also
contains one intentional noindex/non-sitemap prototype area at
`/docs/prototypes/`; this is a local publishing exclusion, not a Search
Console or Bing coverage result.

| Console | Post-processing coverage report | Included | Excluded / blocked / duplicate / failed | Review result |
|---|---|---:|---:|---|
| Google Search Console | Owner-supplied summary of a Codex inspection on 2026-10-02 (America/Chicago): the currently signed-in account showed the welcome screen; “Already started? finish verification” reported “No properties detected” and no properties waiting for verification. | Unknown | Unknown; no coverage report or counts were available | **NOT VERIFIED IN THE CHECKED ACCOUNT** — this does not rule out a property under another account. Property verification, sitemap submission, indexing status, and aggregate counts remain unknown. |
| Bing Webmaster Tools | Owner-supplied status: no account-level verification or sitemap-submission result has been reviewed. | Unknown | Unknown; no account-level coverage report or counts were available | **UNKNOWN / NOT VERIFIED FROM AVAILABLE EVIDENCE** — verification, submission, indexing status, and dates remain unknown. |

These `Unknown` values are deliberate. They are not zero counts and must not be
reported as proof that all sitemap URLs are indexed. The Google entry is an
owner-supplied summary of a Codex observation, not an owner-reviewed result and
not an independent check in this workspace; the checked account's “No
properties detected” message does not establish whether another account has a
verified property. No owner confirmation or reviewer initials were supplied.
No account-identifying screenshot, token, cookie, or credential is included.

The presence of Google Analytics code in
[`assets/js/glee-site-enhancements.js`](../assets/js/glee-site-enhancements.js)
does not prove Search Console property verification or sitemap submission.
Verification dates, sitemap-submission dates, indexing results, and aggregate
counts remain **UNKNOWN** for both consoles. No account setup or sitemap
submission was performed. A future confirmed result requires owner review and
sanitized result evidence from both consoles.

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

The approved Organization identity URLs and their non-secret approval metadata
live in the schema-checked
[`organization-identity-approval.json`](organization-identity-approval.json)
record. The homepage Organization JSON-LD must match that record exactly.

These URLs were already present in the public structured data and are retained
without adding any new social identity. No private account details are recorded
here, and no new identity should be added without owner approval.
