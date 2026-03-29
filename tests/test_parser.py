"""Tests for .scrivx parsing."""

from scrivener_mcp.parser import ScrivxParser


def test_get_binder(parser):
    binder = parser.get_binder()
    assert len(binder) == 3  # Draft, Research, Trash
    assert binder[0].item_type == "DraftFolder"
    assert binder[0].title == "Draft"


def test_binder_hierarchy(parser):
    binder = parser.get_binder()
    draft = binder[0]
    assert len(draft.children) == 2  # Part One, Part Two
    part_one = draft.children[0]
    assert part_one.title == "Part One"
    assert len(part_one.children) == 2  # Chapter 1, Chapter 2


def test_find_by_uuid(parser):
    item = parser.find_by_uuid("33333333-3333-3333-3333-333333333333")
    assert item is not None
    assert item.title == "Chapter 1: The Beginning"


def test_find_by_uuid_not_found(parser):
    assert parser.find_by_uuid("nonexistent") is None


def test_find_by_title_fuzzy(parser):
    matches = parser.find_by_title("homecoming")
    assert len(matches) == 1
    assert matches[0].title == "Chapter 3: Homecoming"


def test_find_by_title_case_insensitive(parser):
    matches = parser.find_by_title("THE BEGINNING")
    assert len(matches) == 1


def test_binder_path(parser):
    parser.get_binder()
    path = parser.binder_path("33333333-3333-3333-3333-333333333333")
    assert path == "Draft > Part One > Chapter 1: The Beginning"


def test_labels(parser):
    labels = parser.get_labels()
    assert any(l.name == "Red" for l in labels.values())


def test_statuses(parser):
    statuses = parser.get_statuses()
    assert any(s.name == "In Progress" for s in statuses.values())


def test_metadata_on_item(parser):
    ch1 = parser.find_by_uuid("33333333-3333-3333-3333-333333333333")
    assert ch1.label == "Red"
    assert ch1.status == "In Progress"


def test_custom_metadata(parser):
    ch3 = parser.find_by_uuid("66666666-6666-6666-6666-666666666666")
    assert ch3.custom_metadata.get("pov_character") == "Elena"


def test_is_locked(parser, scriv_path):
    assert not parser.is_locked()
    lock = scriv_path / "user.lock"
    lock.write_text("test")
    try:
        assert parser.is_locked()
    finally:
        lock.unlink()
