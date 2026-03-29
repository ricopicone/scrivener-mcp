"""Data classes for Scrivener project structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BinderItem:
    """A single item in the Scrivener binder tree."""

    uuid: str
    title: str
    item_type: str  # Text, Folder, DraftFolder, ResearchFolder, TrashFolder
    created: str = ""
    modified: str = ""
    children: list[BinderItem] = field(default_factory=list)

    # Metadata
    include_in_compile: bool = True
    label_id: int = -1
    status_id: int = -1
    section_type: str = ""

    # Resolved names (filled in by parser)
    label: str = ""
    status: str = ""

    # Custom metadata
    custom_metadata: dict[str, str] = field(default_factory=dict)

    @property
    def is_folder(self) -> bool:
        return self.item_type in ("Folder", "DraftFolder", "ResearchFolder", "TrashFolder")

    def walk(self) -> list[BinderItem]:
        """Yield this item and all descendants depth-first."""
        result = [self]
        for child in self.children:
            result.extend(child.walk())
        return result


@dataclass
class LabelDef:
    id: int
    name: str
    color: str = ""


@dataclass
class StatusDef:
    id: int
    name: str


@dataclass
class CustomMetadataFieldDef:
    id: str
    title: str
    field_type: str = "Text"


@dataclass
class SnapshotInfo:
    date: str
    title: str
    filename: str  # e.g. "2024-01-15-14-30-22-0700.rtf"


@dataclass
class SearchMatch:
    uuid: str
    title: str
    binder_path: str
    matches: list[str]  # context snippets
    match_count: int


@dataclass
class ProjectInfo:
    name: str
    path: str
    locked: bool
