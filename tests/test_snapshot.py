"""Tests for snapshot creation and reading."""

import shutil
from pathlib import Path

import pytest

from scrivener_mcp.reader import read_rtf
from scrivener_mcp.snapshot import create_snapshot, list_snapshots, read_snapshot


@pytest.fixture
def writable_project(tmp_path):
    src = Path(__file__).parent / "fixtures" / "TestProject.scriv"
    dst = tmp_path / "TestProject.scriv"
    shutil.copytree(src, dst)
    return dst


def test_create_snapshot(writable_project):
    uuid = "33333333-3333-3333-3333-333333333333"
    snap = create_snapshot(writable_project, uuid, title="Test Snapshot")
    assert snap is not None
    assert snap.title == "Test Snapshot"
    assert snap.filename.endswith(".rtf")


def test_snapshot_appears_in_list(writable_project):
    uuid = "33333333-3333-3333-3333-333333333333"
    create_snapshot(writable_project, uuid, title="My Snap")

    snaps = list_snapshots(writable_project, uuid)
    assert len(snaps) == 1
    assert snaps[0].title == "My Snap"


def test_read_snapshot_content(writable_project):
    uuid = "33333333-3333-3333-3333-333333333333"
    create_snapshot(writable_project, uuid, title="Before Edit")

    snaps = list_snapshots(writable_project, uuid)
    text = read_snapshot(writable_project, uuid, snaps[0])
    assert "Maria" in text  # Original content from Chapter 1


def test_no_snapshot_for_empty_document(writable_project):
    # Part One folder has no content.rtf
    uuid = "22222222-2222-2222-2222-222222222222"
    snap = create_snapshot(writable_project, uuid)
    assert snap is None
