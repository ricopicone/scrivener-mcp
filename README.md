# Scrivener MCP

An MCP server that lets Claude read, search, and write to [Scrivener 3](https://www.literatureandlatte.com/scrivener/overview) projects. Built for writers who want to brainstorm, organize, and work on their manuscripts with Claude naturally -- "read the chapter called Homecoming," "search for mentions of Elena," "update the synopsis for Chapter 3."

## What it does

- **Browse** your binder hierarchy with word counts and metadata
- **Read** any document, chapter, synopsis, or notes by name (fuzzy matching)
- **Search** across all documents with context snippets
- **Write** synopses, notes, and document content with automatic safety controls
- **Snapshot** every change so you can always roll back from Scrivener's UI

## Safety model

Scrivener auto-saves every 2 seconds and does not detect external file changes. Writing to a project while Scrivener has it open **will silently lose your changes**. This server handles that:

- **Lock detection:** Every write checks for Scrivener's `user.lock` file. If Scrivener has the project open, writes are refused with a clear message.
- **Automatic snapshots:** Before any document content is modified, a Scrivener-native snapshot is created. These show up in Scrivener's Snapshots panel so you can compare or restore.
- **Audit log:** Every write operation is logged to `.scrivener-mcp-audit.log` inside the `.scriv` bundle (a hidden file Scrivener ignores). The log records timestamps, what changed, and snapshot references.
- **No structural changes:** The server never modifies the `.scrivx` XML (the project's structural backbone). It only writes to per-document files. This means it cannot corrupt your binder hierarchy.

**Read operations are always safe**, even while Scrivener is open.

---

## Setup

### Prerequisites

- **macOS** (Scrivener 3 for Mac -- the `.scriv` format is a macOS document package)
- **Python 3.10+**
- **Scrivener 3** projects (`.scriv` bundles)

### Step 1: Clone and install

```bash
git clone https://github.com/yourusername/scrivener-mcp.git
cd scrivener-mcp
pip install -e .
```

This installs the `scrivener-mcp` command and the `scrivener_mcp` Python package.

### Step 2: Find your Scrivener projects

Scrivener projects are `.scriv` bundles (directories that look like files in Finder). They're wherever you saved them -- commonly in `~/Documents/` or a synced folder. To find them:

```bash
find ~/Documents -name "*.scriv" -type d 2>/dev/null
```

Note the directory that contains your `.scriv` project(s). For example, if your project is at `~/Documents/My Novel.scriv`, the project directory is `~/Documents`.

### Step 3: Configure Claude

#### Claude Desktop

Add to your Claude Desktop config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "scrivener": {
      "command": "python",
      "args": ["-m", "scrivener_mcp", "--project-dir", "/Users/YOURNAME/Documents/Scrivener"],
      "env": {}
    }
  }
}
```

Replace `/Users/YOURNAME/Documents/Scrivener` with the directory containing your `.scriv` project(s).

**If your projects are in multiple directories**, use `--project` to list them individually:

```json
{
  "mcpServers": {
    "scrivener": {
      "command": "python",
      "args": [
        "-m", "scrivener_mcp",
        "--project", "/Users/YOURNAME/Documents/My Novel.scriv",
        "--project", "/Users/YOURNAME/Dropbox/Short Stories.scriv"
      ],
      "env": {}
    }
  }
}
```

**If `python` isn't found**, use the full path. To find it:

```bash
which python3
```

Then use that path (e.g., `/usr/local/bin/python3`) in place of `"python"` above.

#### Claude Code (CLI)

Add to your Claude Code MCP settings:

```bash
claude mcp add scrivener -- python -m scrivener_mcp --project-dir ~/Documents/Scrivener
```

Or with environment variables instead of CLI args:

```bash
claude mcp add scrivener -e SCRIVENER_PROJECT_DIR=/Users/YOURNAME/Documents/Scrivener -- python -m scrivener_mcp
```

### Step 4: Verify it works

Restart Claude (Desktop or CLI) after changing the config. Then try:

> "List my Scrivener projects"

You should see your projects listed. Then:

> "Show me the binder for [project name]"

### Troubleshooting

**"No Scrivener projects found"**
- Check that the path in your config points to the directory _containing_ `.scriv` bundles, not to the `.scriv` bundle itself (unless you used `--project`).
- The directory is scanned one level deep -- it won't find projects inside nested subdirectories.

**"python: command not found"**
- Use the full path to your Python interpreter. Run `which python3` to find it.
- If you installed with `pyenv`, the shim path is `~/.pyenv/shims/python3`.

**"No module named scrivener_mcp"**
- Make sure you ran `pip install -e .` in the `scrivener-mcp` directory.
- If you have multiple Python versions, make sure the `pip` you used matches the `python` in your config. Try `python3 -m pip install -e .` explicitly.

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

### Writing

| Tool | Description |
|------|-------------|
| `update_synopsis` | Write or update a synopsis (plain text, safest write) |
| `update_notes` | Write or update document notes |
| `update_document` | Replace a document's content (snapshot created first) |
| `append_text` | Append text to a document (snapshot created first) |
| `get_audit_log` | View the log of all write operations |

All write tools:
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
python -m scrivener_mcp [OPTIONS]

Options:
  --project-dir PATH    Directory containing .scriv projects (scanned one level deep)
  --project PATH        Path to a specific .scriv bundle (can be repeated)
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
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with verbose output
pytest -v
```

### Project structure

```
scrivener-mcp/
  src/scrivener_mcp/
    __init__.py
    __main__.py       # Entry point for python -m
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
