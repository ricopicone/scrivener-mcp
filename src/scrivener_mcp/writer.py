"""Safe write operations for Scrivener documents.

Every write function:
1. Checks user.lock — refuses if Scrivener is open
2. Creates a snapshot before modifying content
3. Logs the operation to the audit log
"""

from __future__ import annotations

from pathlib import Path

from scrivener_mcp.audit import log_write
from scrivener_mcp.reader import read_document_content, read_notes, read_synopsis, word_count
from scrivener_mcp.snapshot import create_snapshot


class ScrivenerLockError(Exception):
    """Raised when Scrivener has the project open."""

    pass


def _check_lock(scriv_path: Path) -> None:
    if (scriv_path / "user.lock").exists():
        raise ScrivenerLockError(
            "Scrivener has this project open. Close Scrivener first, then try again."
        )


def _text_to_rtf(text: str) -> str:
    r"""Convert plain text to minimal valid RTF.

    Scrivener will normalize this on next open, so we keep it simple.
    Paragraph breaks (\n\n) become \par, single newlines become \line.
    """
    # Escape RTF special characters
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")

    # Handle Unicode characters (non-ASCII)
    result = []
    for ch in text:
        if ord(ch) > 127:
            result.append(f"\\u{ord(ch)}?")
        else:
            result.append(ch)
    text = "".join(result)

    # Convert paragraph breaks
    text = text.replace("\n\n", "\\par\n")
    text = text.replace("\n", "\\line\n")

    return (
        "{\\rtf1\\ansi\\deff0"
        "{\\fonttbl{\\f0 Times New Roman;}}"
        "\\pard\\plain\\f0\\fs24 "
        + text
        + "}"
    )


def write_synopsis(
    scriv_path: Path, uuid: str, title: str, text: str
) -> dict[str, str]:
    """Write or update a document's synopsis (plain text)."""
    _check_lock(scriv_path)

    data_dir = scriv_path / "Files" / "Data" / uuid
    if not data_dir.exists():
        raise FileNotFoundError(f"No data directory for document {uuid}")

    synopsis_path = data_dir / "synopsis.txt"
    was = "absent" if not synopsis_path.exists() else f"{word_count(read_synopsis(data_dir))} words"

    synopsis_path.write_text(text, encoding="utf-8")

    log_write(
        scriv_path,
        tool_name="write_synopsis",
        uuid=uuid,
        title=title,
        detail=f"synopsis.txt updated (was: {was}, now: {word_count(text)} words)",
    )

    return {
        "status": "ok",
        "message": f"Synopsis updated for \"{title}\".",
        "previous": was,
        "word_count": str(word_count(text)),
    }


def write_notes(scriv_path: Path, uuid: str, title: str, text: str) -> dict[str, str]:
    """Write or update a document's notes (converted to RTF)."""
    _check_lock(scriv_path)

    data_dir = scriv_path / "Files" / "Data" / uuid
    if not data_dir.exists():
        raise FileNotFoundError(f"No data directory for document {uuid}")

    notes_path = data_dir / "notes.rtf"
    was = "absent" if not notes_path.exists() else f"{word_count(read_notes(data_dir))} words"

    rtf_content = _text_to_rtf(text)
    notes_path.write_text(rtf_content, encoding="utf-8")

    log_write(
        scriv_path,
        tool_name="write_notes",
        uuid=uuid,
        title=title,
        detail=f"notes.rtf updated (was: {was}, now: {word_count(text)} words)",
    )

    return {
        "status": "ok",
        "message": f"Notes updated for \"{title}\".",
        "previous": was,
        "word_count": str(word_count(text)),
    }


def write_document(
    scriv_path: Path, uuid: str, title: str, text: str
) -> dict[str, str]:
    """Write or replace a document's main content (converted to RTF).

    Always creates a snapshot before overwriting.
    """
    _check_lock(scriv_path)

    data_dir = scriv_path / "Files" / "Data" / uuid
    if not data_dir.exists():
        raise FileNotFoundError(f"No data directory for document {uuid}")

    # Snapshot before modifying
    snap = create_snapshot(scriv_path, uuid, title="MCP Backup (before write)")
    snap_ref = snap.date if snap else "no-previous-content"

    old_text = read_document_content(data_dir)
    was_wc = word_count(old_text)

    content_path = data_dir / "content.rtf"
    rtf_content = _text_to_rtf(text)
    content_path.write_text(rtf_content, encoding="utf-8")

    new_wc = word_count(text)

    log_write(
        scriv_path,
        tool_name="write_document",
        uuid=uuid,
        title=title,
        detail=f"content.rtf updated (was: {was_wc} words, now: {new_wc} words)",
        snapshot_ref=snap_ref,
    )

    return {
        "status": "ok",
        "message": f"Document \"{title}\" updated. Snapshot created at {snap_ref}. Restore from Scrivener's Snapshots panel if needed.",
        "previous_word_count": str(was_wc),
        "new_word_count": str(new_wc),
        "snapshot": snap_ref,
    }


def append_to_document(
    scriv_path: Path, uuid: str, title: str, text: str
) -> dict[str, str]:
    """Append text to a document's main content.

    Always creates a snapshot before modifying.
    """
    _check_lock(scriv_path)

    data_dir = scriv_path / "Files" / "Data" / uuid
    if not data_dir.exists():
        raise FileNotFoundError(f"No data directory for document {uuid}")

    # Snapshot before modifying
    snap = create_snapshot(scriv_path, uuid, title="MCP Backup (before append)")
    snap_ref = snap.date if snap else "no-previous-content"

    content_path = data_dir / "content.rtf"

    if content_path.exists():
        # Read existing RTF and insert before the final closing brace
        existing = content_path.read_text(encoding="utf-8", errors="replace")
        # Escape and format the new text
        new_text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        # Handle Unicode
        new_parts = []
        for ch in new_text:
            if ord(ch) > 127:
                new_parts.append(f"\\u{ord(ch)}?")
            else:
                new_parts.append(ch)
        new_text = "".join(new_parts)
        new_text = new_text.replace("\n\n", "\\par\n").replace("\n", "\\line\n")

        # Insert paragraph break + new text before final }
        idx = existing.rfind("}")
        if idx >= 0:
            modified = existing[:idx] + "\\par\n" + new_text + "}"
        else:
            # Malformed RTF, just overwrite
            modified = _text_to_rtf(read_document_content(data_dir) + "\n\n" + text)
        content_path.write_text(modified, encoding="utf-8")
    else:
        rtf_content = _text_to_rtf(text)
        content_path.write_text(rtf_content, encoding="utf-8")

    new_wc = word_count(read_document_content(data_dir))

    log_write(
        scriv_path,
        tool_name="append_to_document",
        uuid=uuid,
        title=title,
        detail=f"content.rtf appended (now: {new_wc} words)",
        snapshot_ref=snap_ref,
    )

    return {
        "status": "ok",
        "message": f"Text appended to \"{title}\". Snapshot created at {snap_ref}.",
        "new_word_count": str(new_wc),
        "snapshot": snap_ref,
    }
