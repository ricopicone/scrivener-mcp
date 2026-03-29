"""Read and convert RTF content from Scrivener documents."""

from __future__ import annotations

import re
from pathlib import Path

from striprtf.striprtf import rtf_to_text

# RTF files larger than this likely contain embedded images.
# striprtf is slow on these, so we strip binary data first.
_RTF_SIZE_THRESHOLD = 500_000  # 500 KB


def _fix_surrogates(text: str) -> str:
    """Fix lone surrogates that striprtf sometimes produces from RTF Unicode escapes.

    Surrogates (U+D800-DFFF) are invalid in JSON and will crash MCP serialization.
    Encode to utf-8 with surrogatepass, then decode back, replacing any invalid
    sequences with the proper character or the replacement character.
    """
    try:
        return text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")
    except Exception:
        return text.encode("utf-8", errors="replace").decode("utf-8")


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
    if len(raw) > _RTF_SIZE_THRESHOLD:
        result = _strip_rtf_fast(text)
    else:
        result = rtf_to_text(text)
    return _fix_surrogates(result)


def _strip_rtf_fast(rtf: str) -> str:
    """Strip large RTF files that contain embedded images/PDFs.

    Scrivener embeds images as hex data inside groups like {\\*\\scrivenerpdf ...},
    {\\*\\shppict{\\pict ...}}, etc. These can be megabytes. We remove them first,
    then pass the remaining (small) RTF to striprtf for proper parsing.
    """
    # Remove Scrivener-specific embedded data groups (nested braces)
    text = _remove_balanced_group(rtf, r'\{\\\*\\scrivenerpdf\b')
    text = _remove_balanced_group(text, r'\{\\\*\\scrivenerimage\b')
    text = _remove_balanced_group(text, r'\{\\\*\\shppict\b')
    text = _remove_balanced_group(text, r'\{\\pict\b')
    text = _remove_balanced_group(text, r'\{\\objdata\b')
    # Now the RTF should be small enough for striprtf
    return rtf_to_text(text)


def _remove_balanced_group(text: str, open_pattern: str) -> str:
    """Remove all brace-balanced groups matching the open pattern."""
    compiled = re.compile(open_pattern)
    result = []
    i = 0
    while i < len(text):
        m = compiled.search(text, i)
        if not m:
            result.append(text[i:])
            break
        result.append(text[i:m.start()])
        # Walk forward counting braces to find the matching close
        depth = 0
        j = m.start()
        while j < len(text):
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        i = j
    return ''.join(result)


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


def word_count_fast(data_path: Path) -> int:
    """Estimate word count from RTF file size without parsing.

    RTF overhead is roughly 3-5x the plain text size. Using a divisor of 7
    (bytes per word including RTF markup and average word length) gives a
    reasonable estimate. This avoids expensive RTF parsing for binder views.
    """
    rtf_path = data_path / "content.rtf"
    if not rtf_path.exists():
        return 0
    size = rtf_path.stat().st_size
    if size < 100:  # RTF header alone is ~80-100 bytes
        return 0
    return max(0, (size - 100) // 7)


def has_file(data_path: Path, filename: str) -> bool:
    """Check if a file exists in the document's data directory."""
    return (data_path / filename).exists()
