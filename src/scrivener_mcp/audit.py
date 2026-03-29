"""Audit log for all write operations."""

from __future__ import annotations

import fcntl
from datetime import datetime, timezone
from pathlib import Path


def audit_log_path(scriv_path: Path) -> Path:
    """Return the audit log path inside the .scriv bundle."""
    return scriv_path / ".scrivener-mcp-audit.log"


def log_write(
    scriv_path: Path,
    *,
    tool_name: str,
    uuid: str,
    title: str,
    detail: str,
    snapshot_ref: str = "",
) -> None:
    """Append an entry to the audit log.

    Uses file locking for atomic appends.
    """
    now = datetime.now(timezone.utc).astimezone()
    timestamp = now.isoformat()

    parts = [timestamp, tool_name, f"UUID:{uuid}", f'"{title}"', detail]
    if snapshot_ref:
        parts.append(f"snapshot:{snapshot_ref}")

    line = " | ".join(parts) + "\n"

    log_path = audit_log_path(scriv_path)
    with open(log_path, "a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def read_audit_log(scriv_path: Path, last_n: int = 50) -> str:
    """Read the last N entries from the audit log."""
    log_path = audit_log_path(scriv_path)
    if not log_path.exists():
        return "No write operations have been logged."
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    if last_n and len(lines) > last_n:
        lines = lines[-last_n:]
    return "\n".join(lines)
