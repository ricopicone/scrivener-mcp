"""Tests for .scrivx parsing."""

from scrivener_mcp.parser import ScrivxParser


def test_get_binder_top_level(parser):
    binder = parser.get_binder()
    assert len(binder) == 3  # Draft, Research, Trash
    assert binder[0].item_type == "DraftFolder"
    assert binder[0].title == "Draft"
    assert binder[1].item_type == "ResearchFolder"
    assert binder[2].item_type == "TrashFolder"


def test_binder_hierarchy(parser):
    binder = parser.get_binder()
    draft = binder[0]
    # Front Matter, Part One, Part Two
    assert len(draft.children) == 3
    part_one = draft.children[1]
    assert part_one.title == "Part One"
    # Chapter 1, Chapter 2, Chapter 3: Letters Home
    assert len(part_one.children) == 3


def test_nested_scenes(parser):
    """Chapters contain sub-scenes as children."""
    ch1 = parser.find_by_uuid("33333333-3333-3333-3333-333333333333")
    assert ch1.is_folder
    assert len(ch1.children) == 2
    assert ch1.children[0].title == "The Bookshop"
    assert ch1.children[1].title == "The Market Square"


def test_find_by_uuid(parser):
    item = parser.find_by_uuid("33333333-3333-3333-3333-333333333334")
    assert item is not None
    assert item.title == "The Bookshop"


def test_find_by_uuid_not_found(parser):
    assert parser.find_by_uuid("nonexistent") is None


def test_find_by_title_fuzzy(parser):
    matches = parser.find_by_title("homecoming")
    assert len(matches) == 1
    assert "Homecoming" in matches[0].title


def test_find_by_title_case_insensitive(parser):
    matches = parser.find_by_title("THE BOOKSHOP")
    assert len(matches) == 1


def test_find_by_title_multiple_matches(parser):
    matches = parser.find_by_title("chapter")
    assert len(matches) >= 4  # Chapters 1-5 + Letters Home


def test_binder_path(parser):
    parser.get_binder()
    path = parser.binder_path("33333333-3333-3333-3333-333333333334")
    assert path == "Draft > Part One > Chapter 1: The Beginning > The Bookshop"


def test_binder_path_top_level(parser):
    parser.get_binder()
    path = parser.binder_path("66666666-6666-6666-6666-666666666666")
    assert path == "Draft > Part Two > Chapter 4: Homecoming"


def test_labels(parser):
    labels = parser.get_labels()
    names = {l.name for l in labels.values()}
    assert "Red" in names
    assert "Blue" in names
    assert "Green" in names
    assert "Orange" in names
    assert "Purple" in names


def test_statuses(parser):
    statuses = parser.get_statuses()
    names = {s.name for s in statuses.values()}
    assert "To Do" in names
    assert "In Progress" in names
    assert "First Draft" in names
    assert "Revised Draft" in names
    assert "Final Draft" in names


def test_metadata_label_and_status(parser):
    """Chapter 1 folder has Red label and In Progress status."""
    ch1 = parser.find_by_uuid("33333333-3333-3333-3333-333333333333")
    assert ch1.label == "Red"
    assert ch1.status == "In Progress"


def test_metadata_varies_across_items(parser):
    """Different items have different statuses."""
    ch3 = parser.find_by_uuid("CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC")
    assert ch3.status == "To Do"
    assert ch3.label == "Blue"


def test_custom_metadata(parser):
    ch4 = parser.find_by_uuid("66666666-6666-6666-6666-666666666666")
    assert ch4.custom_metadata.get("pov_character") == "Lena"


def test_custom_metadata_field_definitions(parser):
    fields = parser.get_custom_metadata_fields()
    assert "pov_character" in fields
    assert fields["pov_character"].title == "POV Character"


def test_include_in_compile(parser):
    """Research items are excluded from compile."""
    research = parser.find_by_uuid("77777777-7777-7777-7777-777777777777")
    assert not research.include_in_compile

    bookshop = parser.find_by_uuid("33333333-3333-3333-3333-333333333334")
    assert bookshop.include_in_compile


def test_is_locked(parser, scriv_path):
    assert not parser.is_locked()
    lock = scriv_path / "user.lock"
    lock.write_text("test")
    try:
        assert parser.is_locked()
    finally:
        lock.unlink()


def test_project_targets(parser):
    targets = parser.get_project_targets()
    assert targets.get("draft_target_count") == 80000
    assert targets.get("session_target_count") == 1000


def test_trash_contents(parser):
    """Trash folder contains deleted items."""
    trash = parser.find_by_uuid("99999999-9999-9999-9999-999999999999")
    assert len(trash.children) == 1
    assert "Deleted" in trash.children[0].title
