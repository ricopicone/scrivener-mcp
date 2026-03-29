"""Tests for full-text search."""

from scrivener_mcp.search import search_binder, search_text


def test_search_text_basic(parser):
    results = search_text(parser, "journey")
    assert len(results) >= 1
    titles = [r.title for r in results]
    assert any("Road North" in t for t in titles)


def test_search_text_case_insensitive(parser):
    results = search_text(parser, "JOURNEY")
    assert len(results) >= 1


def test_search_text_in_synopsis(parser):
    results = search_text(
        parser, "homecoming", search_content=False, search_notes=False
    )
    assert len(results) >= 1
    assert any("[synopsis]" in m for r in results for m in r.matches)


def test_search_text_in_notes(parser):
    results = search_text(
        parser, "pacing", search_content=False, search_synopses=False
    )
    assert len(results) >= 1
    assert any("[notes]" in m for r in results for m in r.matches)


def test_search_text_no_results(parser):
    results = search_text(parser, "xyznonexistent")
    assert len(results) == 0


def test_search_text_excludes_trash(parser):
    """Deleted scene contains 'journey' but should not appear in results."""
    results = search_text(parser, "journey")
    for r in results:
        assert "Trash" not in r.binder_path
        assert "Deleted" not in r.title


def test_search_text_context_snippets(parser):
    """Results include surrounding context."""
    results = search_text(parser, "bookshop", context_chars=30)
    assert len(results) >= 1
    # Snippets should contain the match word plus context
    for r in results:
        for m in r.matches:
            assert "bookshop" in m.lower()


def test_search_text_multiple_matches_per_doc(parser):
    """A document with multiple occurrences reports all of them."""
    results = search_text(parser, "journey")
    road_north = [r for r in results if "Road North" in r.title]
    if road_north:
        assert road_north[0].match_count >= 2


def test_search_binder_by_title(parser):
    results = search_binder(parser, title_pattern="chapter")
    assert len(results) >= 4  # Chapters 1-4 + Letters Home + What Remained + New Roots


def test_search_binder_by_type_folder(parser):
    results = search_binder(parser, item_type="Folder")
    assert all(r.is_folder for r in results)
    assert len(results) >= 4  # Front Matter, Part One, Ch1, Ch2, Part Two, Char Notes


def test_search_binder_by_type_text(parser):
    results = search_binder(parser, item_type="Text")
    assert all(not r.is_folder for r in results)
    assert len(results) >= 8


def test_search_binder_by_label(parser):
    results = search_binder(parser, label="Red")
    assert len(results) >= 1
    assert all(r.label == "Red" for r in results)


def test_search_binder_by_status(parser):
    results = search_binder(parser, status="To Do")
    assert len(results) >= 2  # Letters Home + What Remained + New Roots


def test_search_binder_combined_filters(parser):
    results = search_binder(parser, label="Blue", status="To Do")
    assert len(results) >= 1
    for r in results:
        assert r.label == "Blue"
        assert r.status == "To Do"


def test_search_binder_compile_filter(parser):
    results = search_binder(parser, include_in_compile=False)
    assert len(results) >= 3  # Research folder + children
