"""Create and read Scrivener-native snapshots."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

from scrivener_mcp.models import SnapshotInfo
from scrivener_mcp.reader import read_rtf


def snapshots_dir(scriv_path: Path, uuid: str) -> Path:
    """Return the snapshots directory for a document."""
    return scriv_path / "Snapshots" / f"{uuid}.snapshots"


def list_snapshots(scriv_path: Path, uuid: str) -> list[SnapshotInfo]:
    """List all snapshots for a document."""
    snap_dir = snapshots_dir(scriv_path, uuid)
    index_path = snap_dir / "snapshot.indexes"
    if not index_path.exists():
        return []

    tree = etree.parse(str(index_path))
    root = tree.getroot()
    results = []
    for snap_el in root.iter("Snapshot"):
        date = snap_el.get("Date", "")
        title_el = snap_el.find("Title")
        title = title_el.text if title_el is not None and title_el.text else ""
        # Derive filename from date: "2024-01-15 14:30:22 -0700" -> "2024-01-15-14-30-22-0700.rtf"
        filename = _date_to_filename(date)
        results.append(SnapshotInfo(date=date, title=title, filename=filename))
    return results


def read_snapshot(scriv_path: Path, uuid: str, snapshot: SnapshotInfo) -> str:
    """Read a snapshot's RTF content as plain text."""
    snap_dir = snapshots_dir(scriv_path, uuid)
    rtf_path = snap_dir / snapshot.filename
    return read_rtf(rtf_path)


def create_snapshot(
    scriv_path: Path, uuid: str, title: str = "MCP Backup"
) -> SnapshotInfo | None:
    """Create a Scrivener-native snapshot of a document's content.

    Returns the SnapshotInfo if created, None if there's no content to snapshot.
    """
    content_rtf = scriv_path / "Files" / "Data" / uuid / "content.rtf"
    if not content_rtf.exists():
        return None

    now = datetime.now(timezone.utc).astimezone()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S %z")
    # Insert space before timezone offset for Scrivener format: "-0700" -> " -0700"
    # Actually Scrivener format is like "2021-12-15 16:50:19 -0800"
    filename = _date_to_filename(date_str)

    snap_dir = snapshots_dir(scriv_path, uuid)
    snap_dir.mkdir(parents=True, exist_ok=True)

    # Copy the current RTF as the snapshot
    shutil.copy2(str(content_rtf), str(snap_dir / filename))

    # Read the plain text for the index
    plain_text = read_rtf(content_rtf)

    # Update snapshot.indexes
    _update_snapshot_index(snap_dir, date_str, title, plain_text)

    return SnapshotInfo(date=date_str, title=title, filename=filename)


def _update_snapshot_index(
    snap_dir: Path, date_str: str, title: str, plain_text: str
) -> None:
    """Add an entry to the snapshot.indexes XML file."""
    index_path = snap_dir / "snapshot.indexes"

    if index_path.exists():
        tree = etree.parse(str(index_path))
        root = tree.getroot()
    else:
        root = etree.Element("SnapshotIndexes", Version="1.0")
        # Get the UUID from the directory name: "{UUID}.snapshots"
        binder_uuid = snap_dir.name.replace(".snapshots", "")
        root.set("BinderUUID", binder_uuid)

    snap_el = etree.SubElement(root, "Snapshot", Date=date_str)
    title_el = etree.SubElement(snap_el, "Title")
    title_el.text = title
    text_el = etree.SubElement(snap_el, "Text")
    text_el.text = plain_text

    tree = etree.ElementTree(root)
    tree.write(
        str(index_path), xml_declaration=True, encoding="UTF-8", pretty_print=True
    )


def _date_to_filename(date_str: str) -> str:
    """Convert a date string to a snapshot filename.

    '2024-01-15 14:30:22 -0700' -> '2024-01-15-14-30-22-0700.rtf'
    """
    # Remove the space before the timezone offset, replace colons and spaces with dashes
    cleaned = date_str.strip()
    # Handle format "2024-01-15 14:30:22 -0700"
    parts = cleaned.rsplit(" ", 1)  # Split off timezone
    if len(parts) == 2:
        dt_part, tz_part = parts
        tz_part = tz_part.replace(":", "")  # Remove colon from timezone if present
        name = dt_part.replace(" ", "-").replace(":", "-") + "-" + tz_part
    else:
        name = cleaned.replace(" ", "-").replace(":", "-")
    return name + ".rtf"
