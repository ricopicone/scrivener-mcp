"""Tests for full-text search."""

from scrivener_mcp.search import search_binder, search_text


def test_search_text_basic(parser):
    results = search_text(parser, "journey")
    assert len(results) >= 1
    assert any("Chapter 2" in r.title for r in results)


def test_search_text_case_insensitive(parser):
    results = search_text(parser, "JOURNEY")
    assert len(results) >= 1


def test_search_text_in_synopsis(parser):
    results = search_text(parser, "homecoming", search_content=False, search_notes=False)
    assert len(results) >= 1
    assert any("[synopsis]" in m for r in results for m in r.matches)


def test_search_text_no_results(parser):
    results = search_text(parser, "xyznonexistent")
    assert len(results) == 0


def test_search_text_excludes_trash(parser):
    results = search_text(parser, "journey")
    for r in results:
        assert "Trash" not in r.binder_path


def test_search_binder_by_title(parser):
    results = search_binder(parser, title_pattern="chapter")
    assert len(results) == 3  # Chapter 1, 2, 3


def test_search_binder_by_type(parser):
    results = search_binder(parser, item_type="Folder")
    assert all(r.is_folder for r in results)
    assert len(results) >= 2  # Part One, Part Two (+ Draft, Research)


def test_search_binder_by_label(parser):
    results = search_binder(parser, label="Red")
    assert len(results) >= 1
    assert results[0].title == "Chapter 1: The Beginning"
