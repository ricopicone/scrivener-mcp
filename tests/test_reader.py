"""Tests for RTF reading and text extraction."""

from scrivener_mcp.reader import (
    read_document_content,
    read_notes,
    read_synopsis,
    word_count,
    word_count_fast,
)


def test_read_scene_content(parser):
    """Read a scene with Cocoa RTF formatting, smart quotes, and em dashes."""
    data = parser.data_path("33333333-3333-3333-3333-333333333334")
    text = read_document_content(data)
    assert "bookshop" in text.lower()
    assert len(text) > 100


def test_read_content_with_italics(parser):
    """RTF italic markup should be stripped, leaving the text."""
    data = parser.data_path("BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB")
    text = read_document_content(data)
    assert len(text) > 0


def test_read_content_with_bold(parser):
    """Character notes use bold field names — bold markup should be stripped."""
    data = parser.data_path("88888888-8888-8888-8888-888888888881")
    text = read_document_content(data)
    assert "Background" in text
    assert "Motivation" in text


def test_read_empty_document(parser):
    """A valid RTF file with no text content returns empty or whitespace."""
    data = parser.data_path("DDDDDDDD-DDDD-DDDD-DDDD-DDDDDDDDDDDD")
    text = read_document_content(data)
    assert text.strip() == ""


def test_read_missing_content(parser):
    """A directory with no content.rtf returns empty string."""
    data = parser.data_path("EEEEEEEE-EEEE-EEEE-EEEE-EEEEEEEEEEEE")
    text = read_document_content(data)
    assert text == ""


def test_read_synopsis(parser):
    data = parser.data_path("33333333-3333-3333-3333-333333333334")
    text = read_synopsis(data)
    assert len(text) > 0


def test_read_synopsis_missing(parser):
    data = parser.data_path("44444444-4444-4444-4444-444444444446")
    text = read_synopsis(data)
    assert text == ""


def test_read_notes(parser):
    data = parser.data_path("88888888-8888-8888-8888-888888888881")
    text = read_notes(data)
    assert len(text) > 0


def test_read_notes_on_folder(parser):
    """Chapter 2 folder has editorial notes."""
    data = parser.data_path("44444444-4444-4444-4444-444444444444")
    text = read_notes(data)
    assert "tightening" in text.lower() or "pacing" in text.lower()


def test_read_notes_missing(parser):
    data = parser.data_path("33333333-3333-3333-3333-333333333334")
    text = read_notes(data)
    assert text == ""


def test_word_count():
    assert word_count("hello world") == 2
    assert word_count("") == 0
    assert word_count("one two three four five") == 5


def test_word_count_fast(parser):
    """Fast word count estimates from file size."""
    data = parser.data_path("33333333-3333-3333-3333-333333333334")
    est = word_count_fast(data)
    assert est > 0
    # Should be in the right ballpark (not exact)
    text = read_document_content(data)
    actual = word_count(text)
    assert est > actual * 0.3  # at least 30% of actual
    assert est < actual * 3.0  # no more than 3x actual


def test_word_count_fast_missing(parser):
    """Fast word count for missing file returns 0."""
    data = parser.data_path("EEEEEEEE-EEEE-EEEE-EEEE-EEEEEEEEEEEE")
    assert word_count_fast(data) == 0
