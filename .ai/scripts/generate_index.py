#!/usr/bin/env python3
"""
generate_index.py - Builds/updates .ai/manifests/index.json for the project.

Merge behavior:
- Existing descriptions are preserved for paths that still exist.
- If a file's content is unchanged but its path changed (rename/move),
  its description carries over to the new path.
- Entries for paths that no longer exist (and weren't renamed) are dropped.
- New paths get an empty description, to be filled in later (by an AI
  assistant working in the project, per .ai/CONTRACT.md).

Works on Python 3.8+. No third-party dependencies.
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
MANIFEST_DIR = SCRIPT_DIR.parent / "manifests"
OUTPUT_PATH = MANIFEST_DIR / "index.json"
HASHES_PATH = MANIFEST_DIR / ".index_hashes.json"
TASKS_PATH = SCRIPT_DIR.parent / "tasks" / "state.json"
AI_IGNORE_PATH = SCRIPT_DIR.parent / "ignore"
GITIGNORE_PATH = PROJECT_ROOT / ".gitignore"

# Always skipped, regardless of .gitignore or .ai/ignore contents.
DEFAULT_IGNORE_PATTERNS = [
    ".git",
    "node_modules",
    "__pycache__",
    "*.pyc",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "*.egg-info",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".DS_Store",
    "Thumbs.db",
]


def _pattern_to_regex(pattern):
    """Convert one gitignore-style pattern to (compiled_regex, dir_only,
    anchored). Supports: comments/blank lines (filtered by caller),
    leading '/' (root-anchored), trailing '/' (directory-only), '*',
    '**', and '?'. Does not support '!' negation or '[...]' character
    classes - patterns using those are skipped.
    """
    dir_only = pattern.endswith("/")
    if dir_only:
        pattern = pattern[:-1]
    anchored = pattern.startswith("/") or "/" in pattern
    pattern = pattern.lstrip("/")

    regex = ""
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if pattern[i:i + 3] == "**/":
            regex += "(.*/)?"
            i += 3
            continue
        if pattern[i:i + 2] == "**":
            regex += ".*"
            i += 2
            continue
        if c == "*":
            regex += "[^/]*"
        elif c == "?":
            regex += "[^/]"
        else:
            regex += re.escape(c)
        i += 1

    if anchored:
        regex = "^" + regex + "$"
    else:
        regex = "^(.*/)?" + regex + "$"
    return re.compile(regex), dir_only


def _load_pattern_file(path):
    patterns = []
    if not path.exists():
        return patterns
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return patterns
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        try:
            patterns.append(_pattern_to_regex(line))
        except re.error:
            continue
    return patterns


def load_ignore_patterns():
    patterns = []
    for raw in DEFAULT_IGNORE_PATTERNS:
        patterns.append(_pattern_to_regex(raw))
    patterns.extend(_load_pattern_file(GITIGNORE_PATH))
    patterns.extend(_load_pattern_file(AI_IGNORE_PATH))
    return patterns


def is_ignored(rel_posix_path, is_dir, patterns):
    for regex, dir_only in patterns:
        if dir_only and not is_dir:
            continue
        if regex.match(rel_posix_path):
            return True
    return False


def file_hash(path):
    """Return a sha1 hash of the file's contents, or None if unreadable."""
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def load_existing_index():
    if not OUTPUT_PATH.exists():
        return None
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def scan_project():
    """Return (dir_paths, file_paths) as sorted lists of POSIX-style
    relative path strings, skipping anything matched by the ignore
    patterns (pruning ignored directories rather than just filtering
    them out afterward) and the index's own generated files."""
    patterns = load_ignore_patterns()
    self_paths = {
        OUTPUT_PATH.relative_to(PROJECT_ROOT).as_posix(),
        HASHES_PATH.relative_to(PROJECT_ROOT).as_posix(),
    }

    dir_paths = []
    file_paths = []
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        rel_dir = Path(dirpath).relative_to(PROJECT_ROOT).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir

        kept_dirnames = []
        for d in dirnames:
            rel = f"{rel_dir}/{d}" if rel_dir else d
            if is_ignored(rel, True, patterns):
                continue
            kept_dirnames.append(d)
            dir_paths.append(rel)
        dirnames[:] = kept_dirnames

        for fname in filenames:
            rel = f"{rel_dir}/{fname}" if rel_dir else fname
            if rel in self_paths:
                continue
            if is_ignored(rel, False, patterns):
                continue
            file_paths.append(rel)

    return sorted(dir_paths), sorted(file_paths)


def build_index():
    existing = load_existing_index()
    old_dirs = {}
    old_files = {}

    if existing:
        structure = existing.get("structure", {})
        for entry in structure.get("directories", []):
            old_dirs[entry.get("path")] = entry.get("description", "")
        for entry in structure.get("files", []):
            old_files[entry.get("path")] = entry.get("description", "")

    dir_paths, file_paths = scan_project()

    # Rename detection: if a file's content hash matches an old file
    # whose path is now missing, treat it as a rename and carry over
    # the description. Requires hashes recorded on the previous run.
    still_present = set(file_paths)
    old_hashes = {}
    if HASHES_PATH.exists():
        try:
            with open(HASHES_PATH, "r", encoding="utf-8") as f:
                old_hashes = json.load(f)
        except (json.JSONDecodeError, OSError):
            old_hashes = {}

    vanished_old_paths = [p for p in old_files if p not in still_present]
    vanished_by_hash = {}
    for old_path in vanished_old_paths:
        h = old_hashes.get(old_path)
        if h:
            vanished_by_hash[h] = old_path

    new_hashes = {}
    dir_entries = []
    for d in dir_paths:
        dir_entries.append({"path": d, "description": old_dirs.get(d, "")})

    file_entries = []
    for f in file_paths:
        h = file_hash(PROJECT_ROOT / f)
        if h:
            new_hashes[f] = h
        if f in old_files:
            desc = old_files[f]
        elif h and h in vanished_by_hash:
            desc = old_files[vanished_by_hash[h]]
        else:
            desc = ""
        file_entries.append({"path": f, "description": desc})

    project_name = PROJECT_ROOT.name
    old_project = existing.get("project", {}) if existing else {}

    index = {
        "schema_version": "1.0",
        "project": {
            "name": project_name,
            "description": old_project.get("description", ""),
        },
        "entrypoints": existing.get("entrypoints", {}) if existing else {},
        "structure": {
            "directories": dir_entries,
            "files": file_entries,
        },
    }
    return index, new_hashes


def validate_tasks(index):
    """Print warnings (does not fail the run) for task-data problems a
    fresh session should know about before trusting tasks/state.json:
    more than one in_progress task, or tasks referencing files that no
    longer exist per the index just built."""
    if not TASKS_PATH.exists():
        return
    try:
        with open(TASKS_PATH, "r", encoding="utf-8") as f:
            tasks_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: could not read tasks/state.json for validation: {e}")
        return

    known_paths = set()
    for group in ("directories", "files"):
        for entry in index.get("structure", {}).get(group, []):
            known_paths.add(entry["path"])

    tasks = tasks_data.get("tasks", [])
    in_progress = [t for t in tasks if t.get("status") == "in_progress"]
    if len(in_progress) > 1:
        ids = ", ".join(t.get("id", "?") for t in in_progress)
        print(f"WARNING: {len(in_progress)} tasks marked in_progress "
              f"(only one should be at a time): {ids}")

    for t in tasks:
        missing = [p for p in t.get("related_files", []) if p not in known_paths]
        if missing:
            print(f"WARNING: task {t.get('id', '?')} references missing "
                  f"path(s): {', '.join(missing)}")


def main():
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    index, hashes = build_index()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(HASHES_PATH, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Generated {OUTPUT_PATH}")
    validate_tasks(index)


if __name__ == "__main__":
    sys.exit(main())
