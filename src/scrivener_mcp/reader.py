"""Read and convert RTF content from Scrivener documents."""

from __future__ import annotations

from pathlib import Path

from striprtf.striprtf import rtf_to_text


def read_rtf(path: Path) -> str:
    """Read an RTF file and return plain text with paragraph breaks preserved."""
    if not path.exists():
        return ""
    raw = path.read_bytes()
    # Try UTF-8 first, fall back to latin-1
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return rtf_to_text(text)


def read_plain(path: Path) -> str:
    """Read a plain text file."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def word_count(text: str) -> int:
    """Count words in plain text."""
    return len(text.split())


def read_document_content(data_path: Path) -> str:
    """Read content.rtf from a document's data directory."""
    return read_rtf(data_path / "content.rtf")


def read_synopsis(data_path: Path) -> str:
    """Read synopsis.txt from a document's data directory."""
    return read_plain(data_path / "synopsis.txt")


def read_notes(data_path: Path) -> str:
    """Read notes.rtf from a document's data directory."""
    return read_rtf(data_path / "notes.rtf")


def has_file(data_path: Path, filename: str) -> bool:
    """Check if a file exists in the document's data directory."""
    return (data_path / filename).exists()
