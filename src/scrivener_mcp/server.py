"""FastMCP server with Scrivener tool definitions."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastmcp import FastMCP

from scrivener_mcp.audit import read_audit_log
from scrivener_mcp.models import BinderItem
from scrivener_mcp.parser import ScrivxParser
from scrivener_mcp.reader import (
    has_file,
    read_document_content,
    read_notes,
    read_synopsis,
    word_count,
)
from scrivener_mcp.search import search_binder, search_text
from scrivener_mcp.snapshot import list_snapshots, read_snapshot
from scrivener_mcp.writer import (
    ScrivenerLockError,
    append_to_document,
    write_document,
    write_notes,
    write_synopsis,
)

mcp = FastMCP("Scrivener MCP")


# ── Configuration ──


def _get_project_dirs() -> list[Path]:
    """Get configured project directories from environment."""
    dirs = []
    env_dir = os.environ.get("SCRIVENER_PROJECT_DIR")
    if env_dir:
        dirs.append(Path(env_dir))
    env_projects = os.environ.get("SCRIVENER_PROJECTS")
    if env_projects:
        for p in env_projects.split(":"):
            dirs.append(Path(p.strip()))
    return dirs


def _find_projects() -> list[Path]:
    """Find all .scriv bundles in configured directories."""
    projects = []
    for d in _get_project_dirs():
        if d.suffix == ".scriv" and d.is_dir():
            projects.append(d)
        elif d.is_dir():
            for child in sorted(d.iterdir()):
                if child.suffix == ".scriv" and child.is_dir():
                    projects.append(child)
    return projects


def _get_parser(project_path: str) -> ScrivxParser:
    """Get a parser for a project path. Re-parses each time for freshness."""
    path = Path(project_path)
    if not path.exists():
        raise FileNotFoundError(f"Project not found: {project_path}")
    if not path.suffix == ".scriv":
        raise ValueError(f"Not a .scriv project: {project_path}")
    return ScrivxParser(path)


def _resolve_item(
    parser: ScrivxParser, title: str = "", uuid: str = ""
) -> BinderItem:
    """Resolve a document by title or UUID. Raises on ambiguity or not found."""
    if uuid:
        item = parser.find_by_uuid(uuid)
        if not item:
            raise ValueError(f"No document found with UUID: {uuid}")
        return item

    if not title:
        raise ValueError("Provide either a title or UUID.")

    matches = parser.find_by_title(title)
    if not matches:
        raise ValueError(f'No document found matching "{title}".')
    if len(matches) == 1:
        return matches[0]

    # Multiple matches — return helpful message
    match_list = "\n".join(
        f"  - \"{m.title}\" (UUID: {m.uuid}, {m.item_type})" for m in matches[:10]
    )
    raise ValueError(
        f'Multiple documents match "{title}":\n{match_list}\n\n'
        f"Please be more specific or use the UUID."
    )


# ── Binder tree formatting ──


def _format_binder_tree(
    parser: ScrivxParser, items: list[BinderItem], depth: int = 0
) -> str:
    """Format binder items as an indented tree."""
    lines = []
    for item in items:
        indent = "  " * depth
        data_path = parser.data_path(item.uuid)
        wc = ""
        if not item.is_folder:
            text = read_document_content(data_path)
            if text:
                wc = f" ({word_count(text)} words)"
        else:
            # Aggregate word count for folders
            total = _folder_word_count(parser, item)
            if total > 0:
                wc = f" ({total} words total)"

        type_icon = "📁" if item.is_folder else "📄"
        meta_parts = []
        if item.label and item.label != "No Label":
            meta_parts.append(item.label)
        if item.status and item.status != "No Status":
            meta_parts.append(item.status)
        if not item.include_in_compile:
            meta_parts.append("excluded from compile")
        meta_str = f" [{', '.join(meta_parts)}]" if meta_parts else ""

        lines.append(f"{indent}{type_icon} {item.title}{wc}{meta_str}")

        if item.children:
            lines.append(_format_binder_tree(parser, item.children, depth + 1))
    return "\n".join(lines)


def _folder_word_count(parser: ScrivxParser, folder: BinderItem) -> int:
    """Recursively count words in all children of a folder."""
    total = 0
    for child in folder.children:
        if child.is_folder:
            total += _folder_word_count(parser, child)
        else:
            data_path = parser.data_path(child.uuid)
            text = read_document_content(data_path)
            total += word_count(text)
    return total


# ── Tools: Read ──


@mcp.tool()
def list_projects() -> str:
    """List available Scrivener projects in the configured directory."""
    projects = _find_projects()
    if not projects:
        return (
            "No Scrivener projects found. Set SCRIVENER_PROJECT_DIR or "
            "SCRIVENER_PROJECTS environment variable."
        )
    lines = []
    for p in projects:
        parser = ScrivxParser(p)
        locked = "🔒 (Scrivener has it open)" if parser.is_locked() else "✅"
        lines.append(f"- {p.stem} {locked}\n  Path: {p}")
    return "\n".join(lines)


@mcp.tool()
def get_binder(project_path: str) -> str:
    """Return the full binder hierarchy with titles, types, word counts, and metadata.

    Args:
        project_path: Path to the .scriv project bundle
    """
    parser = _get_parser(project_path)
    binder = parser.get_binder()
    if not binder:
        return "Empty binder."
    return _format_binder_tree(parser, binder)


@mcp.tool()
def read_document(project_path: str, title: str = "", uuid: str = "") -> str:
    """Read a document's text content by title or UUID. Strips RTF to plain text.

    Title lookup is fuzzy and case-insensitive.

    Args:
        project_path: Path to the .scriv project bundle
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match, takes precedence over title)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    data_path = parser.data_path(item.uuid)
    text = read_document_content(data_path)
    if not text:
        return f'Document "{item.title}" exists but has no content.'

    wc = word_count(text)
    path = parser.binder_path(item.uuid)
    return f"📍 {path}\n📊 {wc} words\n\n{text}"


@mcp.tool()
def read_document_synopsis(project_path: str, title: str = "", uuid: str = "") -> str:
    """Read a document's synopsis (index card text).

    Args:
        project_path: Path to the .scriv project bundle
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    data_path = parser.data_path(item.uuid)
    text = read_synopsis(data_path)
    if not text:
        return f'No synopsis for "{item.title}".'
    return f"📍 {parser.binder_path(item.uuid)}\n\n{text}"


@mcp.tool()
def read_document_notes(project_path: str, title: str = "", uuid: str = "") -> str:
    """Read a document's notes.

    Args:
        project_path: Path to the .scriv project bundle
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    data_path = parser.data_path(item.uuid)
    text = read_notes(data_path)
    if not text:
        return f'No notes for "{item.title}".'
    return f"📍 {parser.binder_path(item.uuid)}\n\n{text}"


@mcp.tool()
def read_chapter(project_path: str, title: str = "", uuid: str = "") -> str:
    """Read all documents within a folder/chapter, concatenated in binder order.

    Args:
        project_path: Path to the .scriv project bundle
        title: Folder title (fuzzy, case-insensitive match)
        uuid: Folder UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)

    if not item.children:
        # It's a single document, just read it
        data_path = parser.data_path(item.uuid)
        text = read_document_content(data_path)
        wc = word_count(text) if text else 0
        return f"📍 {parser.binder_path(item.uuid)}\n📊 {wc} words\n\n{text}"

    parts = []
    total_wc = 0
    for child in item.children:
        _collect_texts(parser, child, parts)
    for _, _, wc_val in parts:
        total_wc += wc_val

    path = parser.binder_path(item.uuid)
    lines = [f"📍 {path}", f"📊 {total_wc} words total", ""]
    for doc_title, text, wc_val in parts:
        lines.append(f"--- {doc_title} ({wc_val} words) ---")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def _collect_texts(
    parser: ScrivxParser, item: BinderItem, parts: list[tuple[str, str, int]]
) -> None:
    """Recursively collect document texts in binder order."""
    if not item.is_folder:
        data_path = parser.data_path(item.uuid)
        text = read_document_content(data_path)
        wc = word_count(text) if text else 0
        parts.append((item.title, text or "(empty)", wc))
    for child in item.children:
        _collect_texts(parser, child, parts)


@mcp.tool()
def get_document_metadata(project_path: str, title: str = "", uuid: str = "") -> str:
    """Return metadata for a document: word count, label, status, dates, etc.

    Args:
        project_path: Path to the .scriv project bundle
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    data_path = parser.data_path(item.uuid)

    text = read_document_content(data_path)
    wc = word_count(text) if text else 0
    char_count = len(text) if text else 0

    lines = [
        f"Title: {item.title}",
        f"UUID: {item.uuid}",
        f"Type: {item.item_type}",
        f"Binder path: {parser.binder_path(item.uuid)}",
        f"Word count: {wc}",
        f"Character count: {char_count}",
        f"Label: {item.label or 'None'}",
        f"Status: {item.status or 'None'}",
        f"Include in compile: {'Yes' if item.include_in_compile else 'No'}",
        f"Section type: {item.section_type or 'Default'}",
        f"Created: {item.created}",
        f"Modified: {item.modified}",
        f"Has synopsis: {'Yes' if has_file(data_path, 'synopsis.txt') else 'No'}",
        f"Has notes: {'Yes' if has_file(data_path, 'notes.rtf') else 'No'}",
    ]

    if item.custom_metadata:
        fields = parser.get_custom_metadata_fields()
        lines.append("Custom metadata:")
        for fid, value in item.custom_metadata.items():
            field_def = fields.get(fid)
            name = field_def.title if field_def else fid
            lines.append(f"  {name}: {value}")

    return "\n".join(lines)


@mcp.tool()
def search_project_text(
    project_path: str,
    query: str,
    case_sensitive: bool = False,
    use_regex: bool = False,
    search_content: bool = True,
    search_synopses: bool = True,
    search_notes: bool = True,
    context_chars: int = 50,
) -> str:
    """Search across all documents for a text string or regex.

    Args:
        project_path: Path to the .scriv project bundle
        query: Text to search for
        case_sensitive: Whether the search is case-sensitive
        use_regex: Whether to treat query as a regex pattern
        search_content: Search document content
        search_synopses: Search synopses
        search_notes: Search notes
        context_chars: Characters of context to show around each match
    """
    parser = _get_parser(project_path)
    results = search_text(
        parser,
        query,
        case_sensitive=case_sensitive,
        use_regex=use_regex,
        search_content=search_content,
        search_synopses=search_synopses,
        search_notes=search_notes,
        context_chars=context_chars,
    )

    if not results:
        return f'No matches found for "{query}".'

    lines = [f'Found matches in {len(results)} document(s) for "{query}":', ""]
    for r in results:
        lines.append(f"📄 {r.title} ({r.match_count} match{'es' if r.match_count != 1 else ''})")
        lines.append(f"   📍 {r.binder_path}")
        for snippet in r.matches[:5]:  # Limit snippets per document
            lines.append(f"   {snippet}")
        if len(r.matches) > 5:
            lines.append(f"   ... and {len(r.matches) - 5} more matches")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def search_project_binder(
    project_path: str,
    title_pattern: str = "",
    item_type: str = "",
    label: str = "",
    status: str = "",
    include_in_compile: bool | None = None,
) -> str:
    """Search binder items by title and metadata.

    Args:
        project_path: Path to the .scriv project bundle
        title_pattern: Title substring to match (case-insensitive)
        item_type: Filter by type: 'Text', 'Folder', etc.
        label: Filter by label name
        status: Filter by status name
        include_in_compile: Filter by compile inclusion (true/false/omit for any)
    """
    parser = _get_parser(project_path)
    results = search_binder(
        parser,
        title_pattern=title_pattern,
        item_type=item_type,
        label=label,
        status=status,
        include_in_compile=include_in_compile,
    )

    if not results:
        return "No matching binder items found."

    lines = [f"Found {len(results)} matching item(s):", ""]
    for item in results:
        type_icon = "📁" if item.is_folder else "📄"
        path = parser.binder_path(item.uuid)
        meta = []
        if item.label and item.label != "No Label":
            meta.append(item.label)
        if item.status and item.status != "No Status":
            meta.append(item.status)
        meta_str = f" [{', '.join(meta)}]" if meta else ""
        lines.append(f"{type_icon} {path}{meta_str}")
        lines.append(f"   UUID: {item.uuid}")

    return "\n".join(lines)


@mcp.tool()
def list_document_snapshots(
    project_path: str, title: str = "", uuid: str = ""
) -> str:
    """List available snapshots for a document.

    Args:
        project_path: Path to the .scriv project bundle
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    snaps = list_snapshots(parser.scriv_path, item.uuid)

    if not snaps:
        return f'No snapshots for "{item.title}".'

    lines = [f'Snapshots for "{item.title}":', ""]
    for s in snaps:
        title_str = f' — "{s.title}"' if s.title else ""
        lines.append(f"  📸 {s.date}{title_str}")
    return "\n".join(lines)


@mcp.tool()
def read_document_snapshot(
    project_path: str,
    snapshot_date: str,
    title: str = "",
    uuid: str = "",
) -> str:
    """Read a specific snapshot's content.

    Args:
        project_path: Path to the .scriv project bundle
        snapshot_date: The snapshot date string (from list_document_snapshots)
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    snaps = list_snapshots(parser.scriv_path, item.uuid)

    matching = [s for s in snaps if s.date == snapshot_date]
    if not matching:
        available = ", ".join(s.date for s in snaps) if snaps else "none"
        return f"No snapshot with date {snapshot_date}. Available: {available}"

    text = read_snapshot(parser.scriv_path, item.uuid, matching[0])
    wc = word_count(text)
    return f"📸 Snapshot: {matching[0].date}\n📊 {wc} words\n\n{text}"


@mcp.tool()
def get_project_targets(project_path: str) -> str:
    """Return project word count targets and current progress.

    Args:
        project_path: Path to the .scriv project bundle
    """
    parser = _get_parser(project_path)
    targets = parser.get_project_targets()
    if not targets:
        return "No word count targets set for this project."

    # Count current draft words
    binder = parser.get_binder()
    draft_wc = 0
    for top in binder:
        if top.item_type == "DraftFolder":
            draft_wc = _folder_word_count(parser, top)
            break

    lines = ["Project targets:"]
    if "draft_target_count" in targets:
        target = targets["draft_target_count"]
        pct = (draft_wc / target * 100) if target > 0 else 0
        lines.append(f"  Draft target: {target:,} words")
        lines.append(f"  Current draft: {draft_wc:,} words ({pct:.1f}%)")
    if "session_target_count" in targets:
        lines.append(f"  Session target: {targets['session_target_count']:,} words")

    return "\n".join(lines)


@mcp.tool()
def get_labels_and_statuses(project_path: str) -> str:
    """Return the project's defined labels and statuses.

    Args:
        project_path: Path to the .scriv project bundle
    """
    parser = _get_parser(project_path)
    labels = parser.get_labels()
    statuses = parser.get_statuses()

    lines = ["Labels:"]
    for lbl in labels.values():
        lines.append(f"  - {lbl.name}" + (f" ({lbl.color})" if lbl.color else ""))
    lines.append("")
    lines.append("Statuses:")
    for st in statuses.values():
        lines.append(f"  - {st.name}")

    return "\n".join(lines)


# ── Tools: Write (registered conditionally via --enable-writes) ──


def update_synopsis(
    project_path: str, text: str, title: str = "", uuid: str = ""
) -> str:
    """Write or update a document's synopsis (index card text).

    Scrivener must be closed (no user.lock).

    Args:
        project_path: Path to the .scriv project bundle
        text: The synopsis text to write
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    try:
        result = write_synopsis(parser.scriv_path, item.uuid, item.title, text)
        return result["message"]
    except ScrivenerLockError as e:
        return str(e)


def update_notes(
    project_path: str, text: str, title: str = "", uuid: str = ""
) -> str:
    """Write or update a document's notes. Converted to RTF automatically.

    Scrivener must be closed (no user.lock).

    Args:
        project_path: Path to the .scriv project bundle
        text: The notes text to write (plain text, will be converted to RTF)
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    try:
        result = write_notes(parser.scriv_path, item.uuid, item.title, text)
        return result["message"]
    except ScrivenerLockError as e:
        return str(e)


def update_document(
    project_path: str, text: str, title: str = "", uuid: str = ""
) -> str:
    """Write or replace a document's main text content. Creates a snapshot first.

    Scrivener must be closed (no user.lock). A snapshot is always created before
    overwriting so you can restore from Scrivener's Snapshots panel.

    Args:
        project_path: Path to the .scriv project bundle
        text: The document text (plain text, will be converted to RTF)
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    try:
        result = write_document(parser.scriv_path, item.uuid, item.title, text)
        return result["message"]
    except ScrivenerLockError as e:
        return str(e)


def append_text(
    project_path: str, text: str, title: str = "", uuid: str = ""
) -> str:
    """Append text to the end of a document. Creates a snapshot first.

    Scrivener must be closed (no user.lock).

    Args:
        project_path: Path to the .scriv project bundle
        text: Text to append (plain text, will be converted to RTF)
        title: Document title (fuzzy, case-insensitive match)
        uuid: Document UUID (exact match)
    """
    parser = _get_parser(project_path)
    item = _resolve_item(parser, title, uuid)
    try:
        result = append_to_document(parser.scriv_path, item.uuid, item.title, text)
        return result["message"]
    except ScrivenerLockError as e:
        return str(e)


def get_audit_log(project_path: str, last_n: int = 50) -> str:
    """View the log of all write operations performed by this MCP server.

    Args:
        project_path: Path to the .scriv project bundle
        last_n: Number of recent entries to show (default 50)
    """
    parser = _get_parser(project_path)
    return read_audit_log(parser.scriv_path, last_n)


# ── Write tool registration ──

_WRITE_TOOLS = [update_synopsis, update_notes, update_document, append_text, get_audit_log]


def _register_write_tools() -> None:
    """Register write tools with the MCP server. Called only when --enable-writes is set."""
    for func in _WRITE_TOOLS:
        mcp.tool()(func)


# ── Main ──


def main():
    import argparse

    arg_parser = argparse.ArgumentParser(description="Scrivener MCP Server")
    arg_parser.add_argument(
        "--project-dir",
        type=str,
        help="Directory containing .scriv projects",
    )
    arg_parser.add_argument(
        "--project",
        type=str,
        action="append",
        help="Path to a specific .scriv project (can be repeated)",
    )
    arg_parser.add_argument(
        "--enable-writes",
        action="store_true",
        default=False,
        help="Enable write tools (synopsis, notes, document content). Disabled by default.",
    )
    args = arg_parser.parse_args()

    # Set environment from CLI args
    paths = []
    if args.project_dir:
        paths.append(args.project_dir)
    if args.project:
        paths.extend(args.project)

    if paths:
        os.environ["SCRIVENER_PROJECTS"] = ":".join(paths)

    if args.enable_writes:
        _register_write_tools()

    mcp.run()


if __name__ == "__main__":
    main()
