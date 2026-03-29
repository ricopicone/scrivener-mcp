## Scrivener MCP Server — Design

A Python MCP server (FastMCP) that lets Claude read, search, and carefully write to Scrivener 3 (.scriv) projects. Designed for a writer who will brainstorm and organize with Claude while Scrivener is open.

---

### Scrivener project format

A `.scriv` bundle is a macOS document package (directory):

```
ProjectName.scriv/
  ProjectName.scrivx            # XML: binder hierarchy, metadata, labels, statuses
  Files/
    Data/
      {UUID}/
        content.rtf             # Document text (RTF with Cocoa extensions)
        content.comments        # XML: inline comments and footnotes
        content.styles          # Style reference UUID
        synopsis.txt            # Plain-text index card synopsis
        notes.rtf               # Document notes (RTF)
      docs.checksum             # SHA-1 checksums: "uuid/filename=hash"
    binder.autosave             # ZIP backup of .scrivx
    binder.backup               # Another ZIP backup of .scrivx
    styles.xml                  # Project-level style definitions
    version.txt                 # Format version (e.g. "23")
  Settings/
    compile.xml, ui-common.xml, etc.
  Snapshots/
    {UUID}.snapshots/
      YYYY-MM-DD-HH-MM-SS-TZ.rtf   # Snapshot RTF content
      snapshot.indexes              # XML with title, plain text, date
  user.lock                     # Present when Scrivener has the project open
```

The `.scrivx` has a `<Binder>` element with nested `<BinderItem>` elements. Each has attributes `UUID`, `Type` (`Text`, `Folder`, `DraftFolder`, `ResearchFolder`, `TrashFolder`), `Created`, `Modified`. Child elements include `<Title>`, `<MetaData>` (with `<IncludeInCompile>`, `<StatusID>`, `<LabelID>`, `<SectionType>`, `<CustomMetaData>`), and `<Children>`.

Project-level elements include `<LabelSettings>`, `<StatusSettings>`, `<SectionTypes>`, `<CustomMetaDataSettings>`, `<Collections>`, `<ProjectTargets>`.

---

### Concurrent access model

**Critical:** Scrivener auto-saves the active document every 2 seconds. It does NOT watch for external file changes. If you write to a file Scrivener has open, your changes will be silently overwritten.

- `user.lock` exists when Scrivener has the project open
- **Reads are always safe**, even while Scrivener is open
- **Writes require `user.lock` to be absent** — refuse all writes otherwise
- Before any content write, create a Scrivener-format snapshot so the user can roll back from within Scrivener itself

---

### Package structure

```
scrivener-mcp/
  pyproject.toml
  src/
    scrivener_mcp/
      __init__.py
      __main__.py         # Entry point: python -m scrivener_mcp
      server.py           # FastMCP server, tool definitions, config
      parser.py           # .scrivx XML parsing, binder tree, metadata lookups
      reader.py           # RTF-to-text, synopsis/notes reading
      writer.py           # Safe write operations, RTF generation
      snapshot.py         # Snapshot creation and reading
      search.py           # Full-text search across documents
      audit.py            # Write audit log
      models.py           # Data classes (BinderItem, Document, SearchResult, etc.)
  tests/
    conftest.py
    fixtures/             # Minimal .scriv project for testing
    test_parser.py
    test_reader.py
    test_writer.py
    test_snapshot.py
    test_search.py
    test_audit.py
```

Run as: `python -m scrivener_mcp --project-dir /path/to/scrivener/projects`

---

### Tools — Read

#### `list_projects`
List available `.scriv` projects in the configured directory.
Returns: project name, path, whether currently locked by Scrivener.

#### `get_binder`
Return the full binder hierarchy as structured data.
Returns: tree of items with title, UUID, type, nesting depth, has_synopsis, has_notes, word_count, label, status, include_in_compile. Folders show aggregate word count of children.

#### `read_document`
Read a document's text content by title or UUID. Strips RTF to plain text preserving paragraph breaks.
- Title lookup is fuzzy and case-insensitive ("read Homecoming" finds "The Homecoming")
- If multiple matches, return the list and ask for clarification
- Returns: plain text, word count, document path in binder

#### `read_synopsis`
Read a document's synopsis by title or UUID.
Returns: synopsis text, or "No synopsis" if absent.

#### `read_notes`
Read a document's notes by title or UUID. Strips RTF to plain text.
Returns: notes text, or "No notes" if absent.

#### `read_chapter`
Read all documents within a folder by title or UUID, concatenated in binder order.
- Each document separated by a header with its title
- Returns: concatenated text, per-document word counts, total word count

#### `get_document_metadata`
Return metadata for a document: word count, character count, label, status, section type, custom metadata, include_in_compile, created/modified dates.

#### `search_text`
Search across all documents for a text string.
- Case-insensitive by default, with option for regex
- Returns: matching document titles, binder path, match count, and surrounding context (configurable context window, default ~50 chars each side)
- Searches content, synopses, and notes (configurable)

#### `search_binder`
Search binder item titles and metadata.
- Filter by: title pattern, type (folder/text), label, status, include_in_compile
- Returns: matching items with their binder path

#### `list_snapshots`
List available snapshots for a document by title or UUID.
Returns: snapshot dates and titles.

#### `read_snapshot`
Read a specific snapshot's content by document title/UUID and snapshot date or title.
Returns: plain text of the snapshot.

#### `get_project_targets`
Return project and session word count targets and progress.

#### `get_labels_and_statuses`
Return the project's defined labels and statuses (so the user/Claude can reference them).

---

### Tools — Write

All write tools share these safety behaviors:

1. **Lock check:** Refuse if `user.lock` exists. Return a clear message: "Scrivener has this project open. Close it first, then try again."
2. **Snapshot:** Before modifying any content.rtf, automatically create a Scrivener-native snapshot (so the writer can see and restore it from Scrivener's snapshot panel).
3. **Audit log:** Every write is appended to `{project}/.scrivener-mcp-audit.log` with timestamp, tool name, document UUID, document title, what changed, and the user/session that triggered it.
4. **Confirmation context:** Each write tool returns what it did and how to undo it (e.g., "Snapshot created at 2024-01-15 14:30:22 — restore from Scrivener's Snapshots panel").

#### `write_synopsis`
Set or update a document's synopsis by title or UUID.
- **Safest write** — synopsis.txt is plain text, no RTF complexity
- Creates the file if it doesn't exist, overwrites if it does
- Good for: brainstorming index cards, organizing chapter summaries

#### `write_notes`
Set or update a document's notes by title or UUID.
- Converts plain text input to minimal valid RTF
- Creates the file if it doesn't exist
- Good for: leaving research notes, brainstorming notes, reminders

#### `write_document`
Set or update a document's main text content by title or UUID.
- Converts plain text to RTF (preserving paragraph breaks as RTF paragraphs)
- **Always creates a snapshot first**
- Good for: drafting new scenes, rewriting passages after discussion
- Returns previous word count and new word count

#### `append_to_document`
Append text to the end of a document's content.
- Reads existing RTF, inserts new paragraphs before the closing brace
- **Always creates a snapshot first**
- Good for: adding brainstormed paragraphs, continuing a draft
- Returns new total word count

#### `set_label`
Set a document's label by title or UUID. Accepts label name (matched case-insensitively against project's defined labels).

#### `set_status`
Set a document's status by title or UUID. Accepts status name (matched case-insensitively against project's defined statuses).

#### `set_metadata`
Set a custom metadata field on a document. Field name matched against project's defined custom metadata fields.

**Not implemented (too risky):**
- Creating new binder items (requires .scrivx modification)
- Deleting or moving binder items (requires .scrivx modification)
- Renaming binder items (requires .scrivx modification)
- Modifying compile settings
- Any operation that touches the .scrivx XML

The .scrivx is the project's structural backbone. Producing invalid XML or inconsistent state there can make the project unopenable. All write operations are confined to per-document files in `Files/Data/{UUID}/` and the `Snapshots/` directory.

---

### Audit log format

Plain text, one entry per line, appended atomically:

```
2024-01-15T14:30:22-0700 | write_synopsis | UUID:9FFBA333-8432-41C1-91F5-1302DFE283CA | "Chapter 3: Homecoming" | synopsis.txt created (was: absent) | session:abc123
2024-01-15T14:32:05-0700 | write_document | UUID:9FFBA333-8432-41C1-91F5-1302DFE283CA | "Chapter 3: Homecoming" | content.rtf updated (was: 1523 words, now: 1687 words) | snapshot:2024-01-15-14-32-05-0700 | session:abc123
```

The audit log lives inside the `.scriv` bundle so it travels with the project (backups, cloud sync). It's a dotfile so Scrivener ignores it.

---

### Design notes

- **Fuzzy title matching:** Case-insensitive substring match. "homecoming" matches "Chapter 3: The Homecoming". If ambiguous, return all matches and let the user pick.
- **Binder caching:** Parse the .scrivx once per request batch, but don't cache across requests (she'll be editing in Scrivener simultaneously, and the file changes on every auto-save).
- **RTF stripping:** Use `striprtf` for RTF-to-text. Preserve paragraph breaks (`\par`, `\pard`). Strip all formatting codes.
- **RTF generation:** For writes, produce minimal valid RTF. Don't try to preserve or replicate Scrivener's Cocoa RTF extensions — Scrivener will normalize the RTF on next open. Keep it simple: `{\rtf1\ansi\deff0{\fonttbl{\f0 Times New Roman;}}{\colortbl;\red0\green0\blue0;}\pard\plain\f0\fs24 ...text with \par for paragraphs... }`.
- **Snapshot format:** Match Scrivener's native format exactly — timestamp-named RTF file plus `snapshot.indexes` XML update — so snapshots appear in Scrivener's UI.
- **Word counts:** Count words in the stripped plain text (split on whitespace after stripping).
- **Binder path:** Display as "Draft > Part One > Chapter 3 > Scene 2" so the writer knows where things are.
- **Error handling:** Never raise unhandled exceptions to the MCP client. Return clear, human-friendly error messages. Missing files → "No synopsis found for X", lock detected → "Scrivener has this project open — close it before writing".

---

### Dependencies

```
fastmcp
striprtf       # RTF to plain text
lxml            # XML parsing (faster and more robust than stdlib ElementTree)
```

### Configuration

Server accepts:
- `--project-dir PATH` — directory containing .scriv bundles (scans one level deep)
- `--project PATH` — path to a single .scriv bundle (can be repeated)
- Environment variable `SCRIVENER_PROJECT_DIR` as fallback
