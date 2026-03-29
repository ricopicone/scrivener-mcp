"""Full-text search across Scrivener documents."""

from __future__ import annotations

import re
from pathlib import Path

from scrivener_mcp.models import BinderItem, SearchMatch
from scrivener_mcp.parser import ScrivxParser
from scrivener_mcp.reader import read_document_content, read_notes, read_synopsis


def search_text(
    parser: ScrivxParser,
    query: str,
    *,
    case_sensitive: bool = False,
    use_regex: bool = False,
    search_content: bool = True,
    search_synopses: bool = True,
    search_notes: bool = True,
    context_chars: int = 50,
) -> list[SearchMatch]:
    """Search across all documents for a text string or regex."""
    flags = 0 if case_sensitive else re.IGNORECASE
    if use_regex:
        pattern = re.compile(query, flags)
    else:
        pattern = re.compile(re.escape(query), flags)

    binder = parser.get_binder()
    results = []

    for top in binder:
        for item in top.walk():
            if item.item_type == "TrashFolder":
                continue
            # Skip the trash folder's children too
            if _is_in_trash(parser, item.uuid):
                continue

            matches = []
            data_path = parser.data_path(item.uuid)

            if search_content:
                text = read_document_content(data_path)
                matches.extend(_find_matches(pattern, text, context_chars, "content"))

            if search_synopses:
                text = read_synopsis(data_path)
                if text:
                    matches.extend(
                        _find_matches(pattern, text, context_chars, "synopsis")
                    )

            if search_notes:
                text = read_notes(data_path)
                if text:
                    matches.extend(_find_matches(pattern, text, context_chars, "notes"))

            if matches:
                results.append(
                    SearchMatch(
                        uuid=item.uuid,
                        title=item.title,
                        binder_path=parser.binder_path(item.uuid),
                        matches=matches,
                        match_count=len(matches),
                    )
                )

    return results


def _is_in_trash(parser: ScrivxParser, uuid: str) -> bool:
    """Check if a document is inside the trash folder."""
    path = parser.binder_path(uuid)
    return path.startswith("Trash")


def _find_matches(
    pattern: re.Pattern, text: str, context_chars: int, source: str
) -> list[str]:
    """Find all matches with surrounding context."""
    matches = []
    for m in pattern.finditer(text):
        start = max(0, m.start() - context_chars)
        end = min(len(text), m.end() + context_chars)
        snippet = text[start:end]
        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        matches.append(f"[{source}] {snippet}")
    return matches


def search_binder(
    parser: ScrivxParser,
    *,
    title_pattern: str = "",
    item_type: str = "",
    label: str = "",
    status: str = "",
    include_in_compile: bool | None = None,
) -> list[BinderItem]:
    """Search binder items by title and metadata filters."""
    binder = parser.get_binder()
    results = []

    for top in binder:
        for item in top.walk():
            if _is_in_trash(parser, item.uuid):
                continue

            if title_pattern and title_pattern.lower() not in item.title.lower():
                continue
            if item_type and item.item_type.lower() != item_type.lower():
                if item_type.lower() == "folder" and not item.is_folder:
                    continue
                elif item_type.lower() != "folder" and item.item_type.lower() != item_type.lower():
                    continue
            if label and label.lower() != item.label.lower():
                continue
            if status and status.lower() != item.status.lower():
                continue
            if include_in_compile is not None and item.include_in_compile != include_in_compile:
                continue

            results.append(item)

    return results
