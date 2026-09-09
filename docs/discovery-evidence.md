# Discovery and ownership evidence

**Review date:** 2026-09-09
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
  "review_date": "2026-09-09",
  "scope": {
    "source": "config/public-inventory.json + sitemap.xml",
    "url_count": 61,
    "url_sha256": "148f0e51a086db089c6ce79dc50a01409e0e074ed00e66c2adb634f546dbc6f4"
  },
  "records": {
    "google-search-console": {
      "review_date": "2026-09-09",
      "scope": {
        "url_count": 61,
        "url_sha256": "148f0e51a086db089c6ce79dc50a01409e0e074ed00e66c2adb634f546dbc6f4"
      },
      "status": "blocked"
    },
    "bing-webmaster-tools": {
      "review_date": "2026-09-09",
      "scope": {
        "url_count": 61,
        "url_sha256": "148f0e51a086db089c6ce79dc50a01409e0e074ed00e66c2adb634f546dbc6f4"
      },
      "status": "blocked"
    }
  }
}
```

## Post-submission coverage review

**Review date:** 2026-09-09
**Reviewer:** repository review; no console account details accessed
**Coverage scope:** 61 unique sitemap URLs:

- 1 homepage
- 1 Toolbox hub
- 7 branch pages
- 42 Tool-ette pages
- 10 supporting pages

The repository and public preflight confirm that the intended scope is
internally consistent: the generated sitemap contains 61 URLs, every sitemap
URL has a corresponding public file, and the live `robots.txt` and
`sitemap.xml` each return HTTP 200 from the canonical host. The repository also
contains one intentional noindex/non-sitemap prototype area at
`/docs/prototypes/`; this is a local publishing exclusion, not a Search
Console or Bing coverage result.

| Console | Post-processing coverage report | Included | Excluded / blocked / duplicate / failed | Review result |
|---|---|---:|---:|---|
| Google Search Console | Not supplied to this workspace | Unknown | Unknown; no console findings were provided | **BLOCKED** — indexing and sitemap-processing status cannot be confirmed |
| Bing Webmaster Tools | Not supplied to this workspace | Unknown | Unknown; no console findings were provided | **BLOCKED** — indexing and sitemap-processing status cannot be confirmed |

These `Unknown` values are deliberate. They are not zero counts and must not be
reported as proof that all 61 URLs are indexed. No owner confirmation,
reviewer initials, account-identifying screenshot, token, cookie, or credential
was available for this review. The owner must provide sanitized aggregate
counts and the review date from both consoles before this section can be
changed to a confirmed result.

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

**Approval date:** 2026-09-09<br>
**Reviewer confirmation:** Owner confirmed all seven identities as official.

The homepage Organization JSON-LD publishes exactly these seven approved identities:

- `https://overkillhill.com/`
- `https://askjamie.bot/`
- `https://www.linkedin.com/company/overkillhillp3`
- `https://facebook.com/OverKillHillP3/`
- `https://x.com/OverKillHillP3`
- `https://www.youtube.com/@Glee-fullyTools`
- `https://ko-fi.com/gleefullypersonalizabletools`

These URLs were already present in the public structured data and are retained
without adding any new social identity. The owner approved the complete list on
2026-09-09 with no removals or corrections. No private account details are
recorded here, and no new identity should be added without owner approval.
