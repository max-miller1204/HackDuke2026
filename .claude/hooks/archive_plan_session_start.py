#!/usr/bin/env python3
"""
SessionStart hook to archive plans from previous sessions.
Reads plansDirectory from settings and archives plans to {plansDirectory}/YYYY-MM-DD/HH-mm-<descriptive-name>.md

Triggers on: clear, startup (new sessions)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


def get_plans_directory(project_dir: Path) -> Optional[Path]:
    """Get plans directory from settings.json or settings.local.json. Returns None if not configured."""
    # Check settings.local.json first (takes precedence), then settings.json
    for filename in ["settings.local.json", "settings.json"]:
        settings_path = project_dir / ".claude" / filename
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
                plans_dir = settings.get("plansDirectory")
                if plans_dir:
                    # Resolve relative paths against project directory
                    plans_path = Path(plans_dir)
                    if not plans_path.is_absolute():
                        plans_path = project_dir / plans_path
                    return plans_path
            except Exception:
                continue
    return None  # Not configured


def get_most_recent_plan(plans_dir: Path) -> Tuple[Optional[Path], float]:
    """Find the most recently modified plan file in the plans directory (excludes subdirectories)"""
    if not plans_dir.exists():
        return None, 0

    # Only get .md files directly in plans_dir, not in subdirs (which are archives)
    plan_files = [f for f in plans_dir.glob("*.md") if f.is_file()]
    if not plan_files:
        return None, 0

    # Sort by modification time, newest first
    plan_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    newest = plan_files[0]
    return newest, newest.stat().st_mtime


def get_archive_marker_path(project_dir: Path) -> Path:
    """Path to store the hash of the last archived plan"""
    return project_dir / ".claude" / ".last_archived_plan"


def get_content_hash(content: str) -> str:
    """Get a hash of the plan content"""
    return hashlib.md5(content.encode()).hexdigest()


def was_already_archived(project_dir: Path, content: str) -> bool:
    """Check if this exact plan was already archived"""
    marker_path = get_archive_marker_path(project_dir)
    if not marker_path.exists():
        return False

    try:
        stored_hash = marker_path.read_text().strip()
        return stored_hash == get_content_hash(content)
    except Exception:
        return False


def mark_as_archived(project_dir: Path, content: str) -> None:
    """Mark this plan as archived to prevent duplicates"""
    marker_path = get_archive_marker_path(project_dir)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(get_content_hash(content))


def slugify(text: str, max_len: int = 60) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)  # remove non-word chars (except spaces/hyphens)
    text = re.sub(r"[\s_]+", "-", text)   # spaces/underscores to hyphens
    text = re.sub(r"-+", "-", text)       # collapse multiple hyphens
    text = text.strip("-")
    if len(text) > max_len:
        # Truncate at a word boundary
        text = text[:max_len].rsplit("-", 1)[0]
    return text or "untitled"


def extract_plan_name(content: str) -> str:
    """Extract a descriptive name from the plan's markdown content.

    Looks for (in order):
    1. First markdown heading (# Title)
    2. First non-empty line
    Falls back to 'untitled' if nothing found.
    """
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # Match markdown headings: # Title, ## Title, etc.
        heading_match = re.match(r"^#{1,6}\s+(.+)", line)
        if heading_match:
            return slugify(heading_match.group(1))
        # Use first non-empty line as fallback
        return slugify(line)
    return "untitled"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"archive_plan.py: invalid JSON: {e}", file=sys.stderr)
        return 0  # Don't block on JSON errors

    # Get project directory first (needed to read settings)
    project_dir = Path(
        os.environ.get("CLAUDE_PROJECT_DIR")
        or payload.get("cwd")
        or os.getcwd()
    )

    # Get plans directory from settings - exit early if not configured
    plans_dir = get_plans_directory(project_dir)
    if not plans_dir:
        return 0  # No plansDirectory configured, nothing to archive

    # Get the most recent plan file from the plans directory
    plan_path, mtime = get_most_recent_plan(plans_dir)
    if not plan_path:
        return 0

    # Read the plan content
    try:
        content = plan_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"archive_plan.py: failed to read plan: {e}", file=sys.stderr)
        return 0

    if not content:
        return 0

    # Skip if already archived (prevents duplicates)
    if was_already_archived(project_dir, content):
        return 0

    # Create archive path: {plans_dir}/YYYY-MM-DD/HH-mm-<descriptive-name>.md
    now = datetime.now()
    date_folder = now.strftime("%Y-%m-%d")
    time_part = now.strftime("%H-%M")
    plan_name = extract_plan_name(content)

    out_dir = plans_dir / date_folder
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{time_part}-{plan_name}.md"

    # Handle collision (unlikely but safe)
    i = 1
    while out_path.exists():
        out_path = out_dir / f"{time_part}-{plan_name}-{i}.md"
        i += 1

    # Write archived plan with metadata header
    session_id = payload.get("session_id", "unknown")
    source = payload.get("source", "unknown")  # clear, startup, resume, compact
    header = (
        f"# Archived Plan\n\n"
        f"**Source:** `{plan_path.name}`\n"
        f"**Session:** `{session_id}`\n"
        f"**Trigger:** `{source}`\n"
        f"**Archived:** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"---\n\n"
    )

    out_path.write_text(header + content + "\n", encoding="utf-8")
    mark_as_archived(project_dir, content)

    # Delete the original plan file after successful archive
    try:
        plan_path.unlink()
    except Exception as e:
        print(f"archive_plan.py: failed to delete original: {e}", file=sys.stderr)

    print(f"Archived plan to: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
