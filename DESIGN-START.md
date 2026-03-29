Here are instructions you can paste into a fresh Claude Code session:

---

## Build a Scrivener MCP Server

Build a Python MCP server (using FastMCP) that lets Claude read and navigate Scrivener 3 (.scriv) projects. My wife is a writer and will use this with Claude to work on her manuscripts.

### Scrivener project format

A `.scriv` bundle is a directory:
- `{ProjectName}.scrivx` — XML file defining the binder hierarchy (documents, folders, titles, UUIDs)
- `Files/Data/{UUID}/content.rtf` — the actual text content for each binder item
- `Files/Data/{UUID}/synopsis.txt` — optional short summary
- `Files/Data/{UUID}/notes.rtf` — optional document notes
- `Snapshots/` — versioned snapshots of documents

The `.scrivx` XML has a `<Binder>` element containing nested `<BinderItem>` elements with attributes like `UUID`, `Type`, and child `<Title>` elements.

### Requirements

- Python package using FastMCP
- Accept a project path (or directory of projects) as config
- Parse the `.scrivx` binder XML to build the document tree
- Convert RTF content to plain text for reading (use `striprtf` or similar)

### Tools to implement

1. **list_projects** — List available .scriv projects in the configured directory
2. **get_binder** — Return the full binder hierarchy (titles, UUIDs, types, nesting) as structured data
3. **read_document** — Read a document's text content by title or UUID. Strip RTF to plain text.
4. **read_synopsis** — Read a document's synopsis
5. **read_notes** — Read a document's notes
6. **search_text** — Search across all documents for a text string, return matching document titles and surrounding context
7. **get_document_metadata** — Return metadata for a document (word count, label, status, dates)
8. **read_chapter** — Read all documents within a folder/chapter by title or UUID, concatenated in binder order

### Design notes

- Title-based lookup should be fuzzy/case-insensitive so she can say "read the chapter called Homecoming" naturally
- The binder tree should be cached and refreshable (she'll have Scrivener open simultaneously)
- Read-only for now — no writing back to .scriv files
- Handle missing synopsis/notes gracefully (return "No synopsis" etc.)
- Include word counts where relevant
- RTF stripping should preserve paragraph breaks

### Package structure

```
scrivener-mcp/
  pyproject.toml
  src/
    scrivener_mcp/
      __init__.py
      server.py      # FastMCP server and tool definitions
      parser.py      # .scrivx XML parsing and binder tree
      reader.py      # RTF reading and text extraction
  README.md
```

Configure it to run as: `python -m scrivener_mcp.server --project-dir /path/to/her/scrivener/projects`