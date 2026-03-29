"""Tests for RTF reading and text extraction."""

from scrivener_mcp.reader import read_document_content, read_notes, read_synopsis, word_count


def test_read_document_content(parser):
    data = parser.data_path("33333333-3333-3333-3333-333333333333")
    text = read_document_content(data)
    assert "Maria" in text
    assert "bookshop" in text
    assert len(text) > 50


def test_read_synopsis(parser):
    data = parser.data_path("33333333-3333-3333-3333-333333333333")
    text = read_synopsis(data)
    assert len(text) > 0


def test_read_synopsis_missing(parser):
    data = parser.data_path("44444444-4444-4444-4444-444444444444")
    text = read_synopsis(data)
    assert text == ""


def test_read_notes(parser):
    data = parser.data_path("88888888-8888-8888-8888-888888888888")
    text = read_notes(data)
    assert len(text) > 0


def test_read_notes_missing(parser):
    data = parser.data_path("33333333-3333-3333-3333-333333333333")
    text = read_notes(data)
    assert text == ""


def test_word_count():
    assert word_count("hello world") == 2
    assert word_count("") == 0
    assert word_count("one two three four five") == 5
