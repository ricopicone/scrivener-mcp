"""Tests for snapshot creation and reading."""

import shutil
from pathlib import Path

import pytest

from scrivener_mcp.reader import read_document_content
from scrivener_mcp.snapshot import create_snapshot, list_snapshots, read_snapshot

SCENE_UUID = "33333333-3333-3333-3333-333333333334"  # The Bookshop


@pytest.fixture
def writable_project(tmp_path):
    src = Path(__file__).parent / "fixtures" / "TestProject.scriv"
    dst = tmp_path / "TestProject.scriv"
    shutil.copytree(src, dst)
    return dst


def test_create_snapshot(writable_project):
    snap = create_snapshot(writable_project, SCENE_UUID, title="Test Snapshot")
    assert snap is not None
    assert snap.title == "Test Snapshot"
    assert snap.filename.endswith(".rtf")


def test_snapshot_appears_in_list(writable_project):
    create_snapshot(writable_project, SCENE_UUID, title="My Snap")

    snaps = list_snapshots(writable_project, SCENE_UUID)
    assert len(snaps) == 1
    assert snaps[0].title == "My Snap"


def test_read_snapshot_content(writable_project):
    """Snapshot preserves the document content at time of creation."""
    original = read_document_content(writable_project / "Files" / "Data" / SCENE_UUID)
    create_snapshot(writable_project, SCENE_UUID, title="Before Edit")

    snaps = list_snapshots(writable_project, SCENE_UUID)
    text = read_snapshot(writable_project, SCENE_UUID, snaps[0])
    assert "bookshop" in text.lower()


def test_multiple_snapshots(writable_project):
    """Multiple snapshots accumulate in the index."""
    import time

    create_snapshot(writable_project, SCENE_UUID, title="First")
    time.sleep(0.01)  # Ensure different timestamps
    create_snapshot(writable_project, SCENE_UUID, title="Second")

    snaps = list_snapshots(writable_project, SCENE_UUID)
    assert len(snaps) == 2
    titles = {s.title for s in snaps}
    assert "First" in titles
    assert "Second" in titles


def test_no_snapshot_for_empty_document(writable_project):
    """No snapshot created when there's no content.rtf."""
    uuid = "EEEEEEEE-EEEE-EEEE-EEEE-EEEEEEEEEEEE"  # New Roots - no content file
    snap = create_snapshot(writable_project, uuid)
    assert snap is None


def test_no_snapshot_for_folder(writable_project):
    """Folders have no content.rtf, so no snapshot."""
    uuid = "22222222-2222-2222-2222-222222222222"  # Part One folder
    snap = create_snapshot(writable_project, uuid)
    assert snap is None
