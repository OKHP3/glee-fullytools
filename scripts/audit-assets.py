#!/usr/bin/env python3
"""Compatibility entry point for the archived asset-audit generator."""
from __future__ import annotations

import runpy
from pathlib import Path


ARCHIVED_SCRIPT = Path(__file__).resolve().parent / "archive" / "audit-assets.py"


if __name__ == "__main__":
    runpy.run_path(str(ARCHIVED_SCRIPT), run_name="__main__")
