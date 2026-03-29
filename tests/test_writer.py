"""Tests for safe write operations."""

import shutil
from pathlib import Path

import pytest

from scrivener_mcp.reader import read_document_content, read_synopsis, word_count
from scrivener_mcp.snapshot import list_snapshots
from scrivener_mcp.writer import (
    ScrivenerLockError,
    append_to_document,
    write_document,
    write_notes,
    write_synopsis,
)

SCENE_UUID = "33333333-3333-3333-3333-333333333334"  # The Bookshop


@pytest.fixture
def writable_project(tmp_path):
    """Copy the test project to a temp dir for write tests."""
    src = Path(__file__).parent / "fixtures" / "TestProject.scriv"
    dst = tmp_path / "TestProject.scriv"
    shutil.copytree(src, dst)
    return dst


def test_write_synopsis(writable_project):
    result = write_synopsis(writable_project, SCENE_UUID, "The Bookshop", "A revised synopsis.")
    assert result["status"] == "ok"

    data = writable_project / "Files" / "Data" / SCENE_UUID
    text = read_synopsis(data)
    assert text == "A revised synopsis."


def test_write_synopsis_creates_new(writable_project):
    """Writing synopsis to a doc that has none creates the file."""
    uuid = "44444444-4444-4444-4444-444444444446"  # Mountain Pass - no synopsis
    result = write_synopsis(writable_project, uuid, "Mountain Pass", "Rain on the mountain.")
    assert result["status"] == "ok"
    assert result["previous"] == "absent"


def test_write_notes(writable_project):
    result = write_notes(writable_project, SCENE_UUID, "The Bookshop", "Research the history of the building.")
    assert result["status"] == "ok"

    data = writable_project / "Files" / "Data" / SCENE_UUID
    from scrivener_mcp.reader import read_notes

    text = read_notes(data)
    assert "history" in text


def test_write_document_creates_snapshot(writable_project):
    snaps_before = list_snapshots(writable_project, SCENE_UUID)
    assert len(snaps_before) == 0

    write_document(writable_project, SCENE_UUID, "The Bookshop", "Brand new content.")

    snaps_after = list_snapshots(writable_project, SCENE_UUID)
    assert len(snaps_after) == 1
    assert "MCP Backup" in snaps_after[0].title


def test_write_document_content(writable_project):
    write_document(
        writable_project, SCENE_UUID, "The Bookshop",
        "The bell rang as she pushed open the door.\n\nSunlight flooded the empty room."
    )

    data = writable_project / "Files" / "Data" / SCENE_UUID
    text = read_document_content(data)
    assert "bell rang" in text
    assert "Sunlight" in text


def test_append_to_document(writable_project):
    data = writable_project / "Files" / "Data" / SCENE_UUID
    original_wc = word_count(read_document_content(data))

    append_to_document(writable_project, SCENE_UUID, "The Bookshop", "She placed the last book on the shelf.")

    new_text = read_document_content(data)
    assert "last book" in new_text
    assert word_count(new_text) > original_wc


def test_append_creates_snapshot(writable_project):
    append_to_document(writable_project, SCENE_UUID, "The Bookshop", "Extra paragraph.")

    snaps = list_snapshots(writable_project, SCENE_UUID)
    assert len(snaps) == 1
    assert "MCP Backup" in snaps[0].title


def test_lock_prevents_all_writes(writable_project):
    lock = writable_project / "user.lock"
    lock.write_text("locked")

    with pytest.raises(ScrivenerLockError):
        write_synopsis(writable_project, SCENE_UUID, "The Bookshop", "test")

    with pytest.raises(ScrivenerLockError):
        write_document(writable_project, SCENE_UUID, "The Bookshop", "test")

    with pytest.raises(ScrivenerLockError):
        append_to_document(writable_project, SCENE_UUID, "The Bookshop", "test")

    with pytest.raises(ScrivenerLockError):
        write_notes(writable_project, SCENE_UUID, "The Bookshop", "test")


def test_audit_log_created(writable_project):
    write_synopsis(writable_project, SCENE_UUID, "The Bookshop", "Test synopsis")

    log = writable_project / ".scrivener-mcp-audit.log"
    assert log.exists()
    content = log.read_text()
    assert "write_synopsis" in content
    assert SCENE_UUID in content


def test_audit_log_accumulates(writable_project):
    """Multiple writes append to the same log."""
    write_synopsis(writable_project, SCENE_UUID, "The Bookshop", "First")
    write_document(writable_project, SCENE_UUID, "The Bookshop", "Second")

    log = writable_project / ".scrivener-mcp-audit.log"
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2
    assert "write_synopsis" in lines[0]
    assert "write_document" in lines[1]
