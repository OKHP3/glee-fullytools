"""Reverse public URL lookup, with separate discovery and HTML-link contracts.

Discovery accepts rooted routes or URLs on the configured origin, never paths
relative to a source page. It maps extensionless routes to directory indexes
without requiring the file to exist (so consumers can report missing files).
Links instead resolve relative to the source directory and require an existing
file, preferring that file over a directory index. Neither contract may leave
the supplied root, including through percent-encoded traversal or symlinks.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlsplit


def _local_path(url: str, origin: str, *, canonical: bool = False) -> str | None:
    try:
        parsed = urlsplit(url)
        expected = urlsplit(origin)
        if parsed.scheme or parsed.netloc:
            if (parsed.scheme or expected.scheme, parsed.netloc) != (
                expected.scheme, expected.netloc
            ):
                return None
        if canonical and (
            parsed.scheme != expected.scheme
            or parsed.netloc != expected.netloc
            or parsed.query
            or parsed.fragment
        ):
            return None
        path = unquote(parsed.path)
        # Backslashes are path separators on Windows; do not interpret them
        # differently across developer machines. NUL is never a valid filename.
        if "\x00" in path or "\\" in path:
            return None
        return path
    except ValueError:
        return None


def _inside(target: Path, root: Path) -> Path | None:
    try:
        resolved = target.resolve()
        resolved.relative_to(root.resolve())
        return resolved
    except (ValueError, OSError, RuntimeError):
        return None


def discovery_path(
    url: str, root: Path, origin: str, *, canonical: bool = False
) -> Path | None:
    """Map a discovery route to a root-relative path, or reject it.

    Query/fragment parts are ignored unless ``canonical`` is true, which also
    requires an absolute same-origin URL (the sitemap coverage contract).
    """
    clean = _local_path(url, origin, canonical=canonical)
    if clean is None:
        return None
    # An absolute origin with no path represents '/'; an empty relative href
    # is not a discovery route.
    if not clean and urlsplit(url).netloc:
        clean = "/"
    if not clean.startswith("/"):
        return None
    relative = Path(clean.lstrip("/"))
    if clean.endswith("/") or not relative.suffix:
        relative /= "index.html"
    target = _inside(root / relative, root)
    return target.relative_to(root.resolve()) if target is not None else None


def link_target(
    href: str, source_dir: Path, root: Path, origin: str
) -> Path | None:
    """Resolve an existing HTML link/resource, relative to its source directory.

    Empty paths represent that directory's index; callers checking fragment-only
    links on a standalone file must use the actual source file instead.
    """
    clean = _local_path(href, origin)
    if clean is None or _inside(source_dir, root) is None:
        return None
    candidate = (
        root / clean.lstrip("/") if clean.startswith("/")
        else source_dir / (clean or "index.html")
    )
    target = _inside(candidate, root)
    if target is None:
        return None
    if target.is_file():
        return target
    index = _inside(target / "index.html", root)
    return index if index is not None and index.is_file() else None