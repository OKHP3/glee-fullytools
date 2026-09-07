#!/bin/bash
set -e

echo "Post-merge: verifying static site integrity..."

for f in index.html assets/css/theme.css assets/js/app.js; do
  if [ ! -f "$f" ]; then
    echo "ERROR: required file missing: $f" >&2
    exit 1
  fi
done

echo "Post-merge: checking committed search index..."
python3 scripts/build-search-index.py --check

echo "Post-merge: checking committed portfolio stats..."
python3 scripts/sync-portfolio-stats.py --check

echo "Post-merge: checking offline shell and CSS versions..."
python3 scripts/sync-css-version.py --check

echo "Post-merge: checking CSP policies..."
python3 scripts/check-csp.py

echo "Post-merge: validating site structure..."
python3 scripts/validate-site.py

echo "Post-merge: checking links and sitemap..."
python3 scripts/check-links.py --no-report

echo "Post-merge: all checks passed."
