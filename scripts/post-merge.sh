#!/bin/bash
set -e

python3 scripts/build-search-index.py
python3 scripts/sync-portfolio-stats.py
