"""Parse .scrivx XML files and build the binder tree."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from scrivener_mcp.models import (
    BinderItem,
    CustomMetadataFieldDef,
    LabelDef,
    StatusDef,
)


class ScrivxParser:
    """Parses a .scrivx file into structured data."""

    def __init__(self, scriv_path: Path):
        self.scriv_path = scriv_path
        self._tree: etree._ElementTree | None = None
        self._root: etree._Element | None = None
        self._labels: dict[int, LabelDef] | None = None
        self._statuses: dict[int, StatusDef] | None = None
        self._custom_fields: dict[str, CustomMetadataFieldDef] | None = None
        self._uuid_index: dict[str, BinderItem] | None = None
        self._parent_map: dict[str, str] | None = None  # child_uuid -> parent_uuid
        self._binder: list[BinderItem] | None = None

    def _find_scrivx(self) -> Path:
        """Find the .scrivx file inside the .scriv bundle."""
        candidates = list(self.scriv_path.glob("*.scrivx"))
        if not candidates:
            raise FileNotFoundError(f"No .scrivx file found in {self.scriv_path}")
        return candidates[0]

    def _ensure_parsed(self) -> None:
        if self._root is not None:
            return
        scrivx = self._find_scrivx()
        self._tree = etree.parse(str(scrivx))
        self._root = self._tree.getroot()

    @property
    def root(self) -> etree._Element:
        self._ensure_parsed()
        return self._root  # type: ignore

    def reload(self) -> None:
        """Force re-parse of the .scrivx file."""
        self._tree = None
        self._root = None
        self._labels = None
        self._statuses = None
        self._custom_fields = None
        self._uuid_index = None
        self._parent_map = None
        self._binder = None

    # ── Labels & Statuses ──

    def get_labels(self) -> dict[int, LabelDef]:
        if self._labels is not None:
            return self._labels
        self._labels = {}
        for label_el in self.root.iter("Label"):
            lid = int(label_el.get("ID", "-1"))
            color = label_el.get("Color", "")
            name = label_el.text or ""
            self._labels[lid] = LabelDef(id=lid, name=name, color=color)
        return self._labels

    def get_statuses(self) -> dict[int, StatusDef]:
        if self._statuses is not None:
            return self._statuses
        self._statuses = {}
        for status_el in self.root.iter("Status"):
            sid = int(status_el.get("ID", "-1"))
            name = status_el.text or ""
            self._statuses[sid] = StatusDef(id=sid, name=name)
        return self._statuses

    def get_custom_metadata_fields(self) -> dict[str, CustomMetadataFieldDef]:
        if self._custom_fields is not None:
            return self._custom_fields
        self._custom_fields = {}
        settings = self.root.find(".//CustomMetaDataSettings")
        if settings is not None:
            for field_el in settings.iter("MetaDataField"):
                fid = field_el.get("ID", "")
                ftype = field_el.get("Type", "Text")
                title_el = field_el.find("Title")
                title = title_el.text if title_el is not None else fid
                self._custom_fields[fid] = CustomMetadataFieldDef(
                    id=fid, title=title, field_type=ftype
                )
        return self._custom_fields

    def label_name(self, label_id: int) -> str:
        labels = self.get_labels()
        lbl = labels.get(label_id)
        return lbl.name if lbl else ""

    def status_name(self, status_id: int) -> str:
        statuses = self.get_statuses()
        st = statuses.get(status_id)
        return st.name if st else ""

    # ── Binder Parsing ──

    def _parse_binder_item(self, el: etree._Element) -> BinderItem:
        uuid = el.get("UUID", "")
        item_type = el.get("Type", "Text")
        created = el.get("Created", "")
        modified = el.get("Modified", "")

        title_el = el.find("Title")
        title = title_el.text if title_el is not None else ""

        # Metadata
        include = True
        label_id = -1
        status_id = -1
        section_type = ""
        custom_metadata: dict[str, str] = {}

        meta = el.find("MetaData")
        if meta is not None:
            inc_el = meta.find("IncludeInCompile")
            if inc_el is not None:
                include = inc_el.text != "No"

            lid_el = meta.find("LabelID")
            if lid_el is not None and lid_el.text:
                label_id = int(lid_el.text)

            sid_el = meta.find("StatusID")
            if sid_el is not None and sid_el.text:
                status_id = int(sid_el.text)

            st_el = meta.find("SectionType")
            if st_el is not None and st_el.text:
                section_type = st_el.text

            cmd = meta.find("CustomMetaData")
            if cmd is not None:
                for item in cmd.iter("MetaDataItem"):
                    fid_el = item.find("FieldID")
                    val_el = item.find("Value")
                    if fid_el is not None and fid_el.text:
                        custom_metadata[fid_el.text] = (
                            val_el.text if val_el is not None and val_el.text else ""
                        )

        # Children
        children = []
        children_el = el.find("Children")
        if children_el is not None:
            for child_el in children_el.findall("BinderItem"):
                children.append(self._parse_binder_item(child_el))

        item = BinderItem(
            uuid=uuid,
            title=title,
            item_type=item_type,
            created=created,
            modified=modified,
            children=children,
            include_in_compile=include,
            label_id=label_id,
            status_id=status_id,
            section_type=section_type,
            label=self.label_name(label_id),
            status=self.status_name(status_id),
            custom_metadata=custom_metadata,
        )
        return item

    def get_binder(self) -> list[BinderItem]:
        """Return top-level binder items (Draft, Research, Trash, etc.)."""
        if self._binder is not None:
            return self._binder
        binder_el = self.root.find(".//Binder")
        if binder_el is None:
            return []
        items = []
        for child_el in binder_el.findall("BinderItem"):
            items.append(self._parse_binder_item(child_el))
        self._binder = items
        self._build_indexes()
        return self._binder

    def _build_indexes(self) -> None:
        self._uuid_index = {}
        self._parent_map = {}
        binder = self._binder or []
        for top in binder:
            for item in top.walk():
                self._uuid_index[item.uuid] = item
            self._build_parent_map(top, None)

    def _build_parent_map(self, item: BinderItem, parent_uuid: str | None) -> None:
        if parent_uuid is not None:
            self._parent_map[item.uuid] = parent_uuid  # type: ignore
        for child in item.children:
            self._build_parent_map(child, item.uuid)

    def find_by_uuid(self, uuid: str) -> BinderItem | None:
        self.get_binder()
        return (self._uuid_index or {}).get(uuid)

    def find_by_title(self, title: str) -> list[BinderItem]:
        """Fuzzy case-insensitive title search. Returns all matches."""
        self.get_binder()
        query = title.lower()
        results = []
        for item in (self._uuid_index or {}).values():
            if query in item.title.lower():
                results.append(item)
        return results

    def binder_path(self, uuid: str) -> str:
        """Return binder path like 'Draft > Chapter 1 > Scene 2'."""
        self.get_binder()
        parts = []
        current = uuid
        while current:
            item = (self._uuid_index or {}).get(current)
            if item:
                parts.append(item.title)
            current = (self._parent_map or {}).get(current, "")  # type: ignore
        parts.reverse()
        return " > ".join(parts)

    def data_path(self, uuid: str) -> Path:
        """Return the Files/Data/{UUID}/ path for a document."""
        return self.scriv_path / "Files" / "Data" / uuid

    def is_locked(self) -> bool:
        """Check if Scrivener has this project open."""
        return (self.scriv_path / "user.lock").exists()

    # ── Project Targets ──

    def get_project_targets(self) -> dict:
        targets_el = self.root.find(".//ProjectTargets")
        result: dict = {}
        if targets_el is None:
            return result
        draft_target = targets_el.find("DraftTarget")
        if draft_target is not None:
            result["draft_target"] = int(draft_target.get("Type", "0") == "Words")
            result["draft_target_count"] = int(draft_target.text or "0")
        session_target = targets_el.find("SessionTarget")
        if session_target is not None:
            result["session_target_count"] = int(session_target.text or "0")
        return result
