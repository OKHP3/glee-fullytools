#!/bin/bash
set -e

echo "Post-merge: verifying static site integrity..."

for f in index.html assets/css/theme.css assets/js/app.js; do
  if [ ! -f "$f" ]; then
    echo "ERROR: required file missing: $f" >&2
    exit 1
  fi
done

echo "Post-merge: rebuilding search index..."
python3 scripts/build-search-index.py

echo "Post-merge: syncing portfolio stats..."
python3 scripts/sync-portfolio-stats.py

echo "Post-merge: all checks passed."
