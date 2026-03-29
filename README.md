# Scrivener MCP

An MCP server that lets Claude read, search, and write to [Scrivener 3](https://www.literatureandlatte.com/scrivener/overview) projects. Built for writers who want to brainstorm, organize, and work on their manuscripts with Claude naturally -- "read the chapter called Homecoming," "search for mentions of Elena," "update the synopsis for Chapter 3."

## What it does

- **Browse** your binder hierarchy with word counts and metadata
- **Read** any document, chapter, synopsis, or notes by name (fuzzy matching)
- **Search** across all documents with context snippets
- **Write** synopses, notes, and document content with automatic safety controls (disabled by default)
- **Snapshot** every change so you can always roll back from Scrivener's UI

## Safety model

Scrivener auto-saves every 2 seconds and does not detect external file changes. Writing to a project while Scrivener has it open **will silently lose your changes**. This server handles that:

- **Write tools are disabled by default.** Pass `--enable-writes` to opt in.
- **Lock detection:** Every write checks for Scrivener's `user.lock` file. If Scrivener has the project open, writes are refused with a clear message.
- **Automatic snapshots:** Before any document content is modified, a Scrivener-native snapshot is created. These show up in Scrivener's Snapshots panel so you can compare or restore.
- **Audit log:** Every write operation is logged to `.scrivener-mcp-audit.log` inside the `.scriv` bundle (a hidden file Scrivener ignores). The log records timestamps, what changed, and snapshot references.
- **No structural changes:** The server never modifies the `.scrivx` XML (the project's structural backbone). It only writes to per-document files. This means it cannot corrupt your binder hierarchy.

**Read operations are always safe**, even while Scrivener is open.

---

## Setup

### 1. Install uv

This project uses [uv](https://docs.astral.sh/uv/) to manage its Python environment automatically. No global Python packages to install or maintain.

If you don't have `uv` yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone this repo

```bash
git clone https://github.com/ricopicone/scrivener-mcp.git
```

That's it -- no `pip install` step. `uv` handles dependencies automatically when the server runs.

### 3. Find your Scrivener projects

Scrivener projects are `.scriv` bundles (directories that look like files in Finder). They're wherever you saved them -- commonly in `~/Documents/` or a synced folder. To find them:

```bash
find ~/Documents -name "*.scriv" -type d 2>/dev/null
```

Note the path. For example, if your project is at `~/Documents/My Novel.scriv`, the project directory is `~/Documents`.

### 4. Configure Claude

Pick the Claude interface you're using:

#### Claude Desktop

Edit the config file at `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scrivener": {
      "command": "/Users/YOURNAME/.local/bin/uv",
      "args": [
        "run",
        "--directory", "/path/to/scrivener-mcp",
        "scrivener-mcp",
        "--project-dir", "/path/to/your/scrivener/projects"
      ]
    }
  }
}
```

Replace the paths:
- `/Users/YOURNAME/.local/bin/uv` -- full path to `uv` (run `which uv` in Terminal to find it). Claude Desktop doesn't inherit your shell PATH, so the full path is required.
- `/path/to/scrivener-mcp` -- where you cloned this repo
- `/path/to/your/scrivener/projects` -- directory containing your `.scriv` bundles

**Example** with real paths:

```json
{
  "mcpServers": {
    "scrivener": {
      "command": "/Users/jane/.local/bin/uv",
      "args": [
        "run",
        "--directory", "/Users/jane/scrivener-mcp",
        "scrivener-mcp",
        "--project-dir", "/Users/jane/Documents"
      ]
    }
  }
}
```

**Multiple project directories:** Use `--project` to list specific `.scriv` bundles:

```json
{
  "mcpServers": {
    "scrivener": {
      "command": "/Users/YOURNAME/.local/bin/uv",
      "args": [
        "run",
        "--directory", "/path/to/scrivener-mcp",
        "scrivener-mcp",
        "--project", "/Users/jane/Documents/My Novel.scriv",
        "--project", "/Users/jane/Dropbox/Short Stories.scriv"
      ]
    }
  }
}
```

#### Claude Code (CLI)

```bash
claude mcp add scrivener -- \
  uv run --directory /path/to/scrivener-mcp \
  scrivener-mcp --project-dir /path/to/your/scrivener/projects
```

### 5. Verify it works

Restart Claude after changing the config. Then try:

> "List my Scrivener projects"

You should see your projects listed. Then:

> "Show me the binder for [project name]"

### Troubleshooting

**"No Scrivener projects found"**
- `--project-dir` should point to the directory _containing_ `.scriv` bundles, not to a `.scriv` bundle itself (use `--project` for that).
- The directory is scanned one level deep -- it won't find projects in nested subdirectories.

**"Failed to spawn process" or "uv: command not found" (Claude Desktop)**
- Make sure the `"command"` value is the full path to `uv` (e.g., `/Users/jane/.local/bin/uv`). Claude Desktop does not inherit your shell PATH. Run `which uv` in Terminal to find the path.

**"error: Failed to resolve"**
- Make sure the `--directory` path points to where you cloned this repo (the directory containing `pyproject.toml`).

**Write refused: "Scrivener has this project open"**
- This is intentional. Close Scrivener before writing, then reopen it after. Scrivener will pick up the changes on next open.

---

## Tools reference

### Reading

| Tool | Description |
|------|-------------|
| `list_projects` | List available `.scriv` projects and whether Scrivener has each one open |
| `get_binder` | Show the full binder tree with word counts, labels, statuses |
| `read_document` | Read a document's text by title or UUID |
| `read_document_synopsis` | Read a document's index card synopsis |
| `read_document_notes` | Read a document's inspector notes |
| `read_chapter` | Read all documents in a folder, concatenated in binder order |
| `get_document_metadata` | Full metadata: word count, label, status, dates, custom fields |
| `search_project_text` | Full-text search across all documents with context snippets |
| `search_project_binder` | Search binder by title, type, label, or status |
| `list_document_snapshots` | List a document's snapshots |
| `read_document_snapshot` | Read a specific snapshot's content |
| `get_project_targets` | Word count targets and progress |
| `get_labels_and_statuses` | List the project's defined labels and statuses |

### Writing (disabled by default)

Write tools are **not available** unless you pass `--enable-writes` when starting the server. This is a deliberate safety default.

| Tool | Description |
|------|-------------|
| `update_synopsis` | Write or update a synopsis (plain text, safest write) |
| `update_notes` | Write or update document notes |
| `update_document` | Replace a document's content (snapshot created first) |
| `append_text` | Append text to a document (snapshot created first) |
| `get_audit_log` | View the log of all write operations |

To enable, add `--enable-writes` to the args in your config:

```json
"args": ["run", "--directory", "/path/to/scrivener-mcp", "scrivener-mcp", "--project-dir", "/path", "--enable-writes"]
```

When enabled, all write tools:
1. Refuse if Scrivener has the project open (`user.lock`)
2. Create a Scrivener-native snapshot before modifying content (visible in Scrivener's Snapshots panel)
3. Log the operation to the audit log

### Title matching

All tools that accept a `title` parameter use **fuzzy, case-insensitive matching**:

- `"homecoming"` matches `"Chapter 3: Homecoming"`
- `"chapter 3"` matches `"Chapter 3: Homecoming"`
- If multiple documents match, the tool lists them and asks you to be more specific

You can also use the `uuid` parameter for exact matching (get UUIDs from `get_binder` or `search_project_binder`).

---

## Using it for writing workflows

Here are some natural ways to work with Claude through this server:

**Brainstorming index cards:**
> "Read the binder for my novel. Then let's brainstorm synopses for the chapters that don't have one yet."

Claude reads the binder, identifies chapters missing synopses, and you discuss what each chapter is about. Then Claude writes the synopses.

**Reviewing and discussing a chapter:**
> "Read Chapter 5. What do you think about the pacing?"

**Searching for consistency:**
> "Search for all mentions of Elena's eye color. I want to make sure it's consistent."

**Organizing with metadata:**
> "Show me all documents with status 'To Do'. Let's figure out what to work on next."

**Drafting new scenes:**
> "Read the synopsis for the next chapter. Let's draft an opening scene together, then write it."

After discussing and drafting, Claude can write or append to the document. A snapshot is always created first.

---

## Configuration reference

### CLI arguments

```
scrivener-mcp [OPTIONS]

Options:
  --project-dir PATH    Directory containing .scriv projects (scanned one level deep)
  --project PATH        Path to a specific .scriv bundle (can be repeated)
  --enable-writes       Enable write tools (disabled by default)
```

### Environment variables

| Variable | Description |
|----------|-------------|
| `SCRIVENER_PROJECT_DIR` | Directory containing `.scriv` projects |
| `SCRIVENER_PROJECTS` | Colon-separated list of paths (directories or `.scriv` bundles) |

CLI arguments set these environment variables internally. You can use either approach.

---

## Development

```bash
# Run tests
uv run --extra dev pytest

# Run tests with verbose output
uv run --extra dev pytest -v

# Run the server directly
uv run scrivener-mcp --project-dir /path/to/projects
```

### Project structure

```
scrivener-mcp/
  pyproject.toml
  src/scrivener_mcp/
    __init__.py
    __main__.py       # Entry point
    server.py         # FastMCP server and tool definitions
    parser.py         # .scrivx XML parsing and binder tree
    reader.py         # RTF-to-text and file reading
    writer.py         # Safe write operations
    snapshot.py       # Scrivener-native snapshot creation/reading
    search.py         # Full-text and binder search
    audit.py          # Write operation audit log
    models.py         # Data classes
  tests/
    fixtures/         # Test .scriv project
    test_parser.py
    test_reader.py
    test_search.py
    test_writer.py
    test_snapshot.py
```

---

## What this server will never do

To protect your work, this server is deliberately limited:

- **Never modifies the `.scrivx` file.** This is the project's structural backbone -- the binder hierarchy, section types, and project settings. A bad edit here can make the project unopenable.
- **Never creates, deletes, moves, or renames binder items.** These all require `.scrivx` changes.
- **Never writes while Scrivener is open.** The lock check is mandatory and cannot be bypassed.
- **Never modifies compile settings, UI state, or project preferences.**

If you need structural changes (new documents, reorganizing), do those in Scrivener. This server handles the content within that structure.
