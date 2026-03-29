"""Tests for safe write operations."""

import shutil
from pathlib import Path

import pytest

from scrivener_mcp.parser import ScrivxParser
from scrivener_mcp.reader import read_document_content, read_synopsis, word_count
from scrivener_mcp.snapshot import list_snapshots
from scrivener_mcp.writer import (
    ScrivenerLockError,
    append_to_document,
    write_document,
    write_synopsis,
)


@pytest.fixture
def writable_project(tmp_path):
    """Copy the test project to a temp dir for write tests."""
    src = Path(__file__).parent / "fixtures" / "TestProject.scriv"
    dst = tmp_path / "TestProject.scriv"
    shutil.copytree(src, dst)
    return dst


def test_write_synopsis(writable_project):
    uuid = "33333333-3333-3333-3333-333333333333"
    result = write_synopsis(writable_project, uuid, "Ch1", "A new synopsis.")
    assert result["status"] == "ok"

    data = writable_project / "Files" / "Data" / uuid
    text = read_synopsis(data)
    assert text == "A new synopsis."


def test_write_document_creates_snapshot(writable_project):
    uuid = "33333333-3333-3333-3333-333333333333"

    # Verify no snapshots initially
    snaps_before = list_snapshots(writable_project, uuid)
    assert len(snaps_before) == 0

    write_document(writable_project, uuid, "Ch1", "Brand new content.")

    snaps_after = list_snapshots(writable_project, uuid)
    assert len(snaps_after) == 1
    assert "MCP Backup" in snaps_after[0].title


def test_write_document_content(writable_project):
    uuid = "33333333-3333-3333-3333-333333333333"
    write_document(writable_project, uuid, "Ch1", "Hello world.\n\nSecond paragraph.")

    data = writable_project / "Files" / "Data" / uuid
    text = read_document_content(data)
    assert "Hello world" in text
    assert "Second paragraph" in text


def test_append_to_document(writable_project):
    uuid = "33333333-3333-3333-3333-333333333333"
    data = writable_project / "Files" / "Data" / uuid
    original_wc = word_count(read_document_content(data))

    append_to_document(writable_project, uuid, "Ch1", "Appended text here.")

    new_text = read_document_content(data)
    assert "Appended text here" in new_text
    assert word_count(new_text) > original_wc


def test_lock_prevents_writes(writable_project):
    lock = writable_project / "user.lock"
    lock.write_text("locked")

    with pytest.raises(ScrivenerLockError):
        write_synopsis(writable_project, "33333333-3333-3333-3333-333333333333", "Ch1", "test")


def test_audit_log_created(writable_project):
    uuid = "33333333-3333-3333-3333-333333333333"
    write_synopsis(writable_project, uuid, "Ch1", "Test synopsis")

    log = writable_project / ".scrivener-mcp-audit.log"
    assert log.exists()
    content = log.read_text()
    assert "write_synopsis" in content
    assert uuid in content
