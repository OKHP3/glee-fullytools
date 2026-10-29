"""Constants shared by browser theme checks and their failure summaries."""

import re

ROUTE_REASON_CODES = frozenset({
    "navigation_failed", "evidence_collection_failed", "theme_assertion_failed",
    "keyboard_recovery_failed", "route_check_failed",
})
PUBLIC_ROUTE_PATTERN = re.compile(r"^/(?:[a-z0-9][a-z0-9-]*/)*(?:[a-z0-9][a-z0-9-]*\.html)?$")
UTILITY_ROUTES = ("/404.html", "/under-construction.html", "/offline.html")
DISABLED_STORAGE_ROUTES = ("/", *UTILITY_ROUTES)
