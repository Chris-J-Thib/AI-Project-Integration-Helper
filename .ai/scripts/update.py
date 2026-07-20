#!/usr/bin/env python3
"""
update.py - Applies a batch of .ai state updates from a single JSON
payload. Exists for AI assistants with no direct file/execution access
to this project (e.g. a plain web chat): the AI generates the JSON
payload and a ready-to-run command, the human runs it in their own
terminal, and reports the output back if needed.

Usage:
    update.py <base64-encoded-json>      (what an AI-generated command uses)
    update.py < payload.json             (stdin, for direct human use)

Does NOT rebuild the file/folder index - that only happens via
generate_index.py (run automatically at the start of every session),
since only a real directory scan can know the current structure.
This script only edits data: STATE.md fields, tasks, index
descriptions/entrypoints for paths that already exist, and (with
explicit confirmation already given in conversation) PROJECT_RULES.md.

Payload shape (all top-level keys optional):
{
  "expected_hashes": {
    ".ai/STATE.md": "<sha1 you last saw for this file>",
    ".ai/tasks/state.json": "..."
  },
  "state": {
    "project_goal": "...",
    "current_status": "...",
    "resume_guidance": "...",
    "notes": "...",
    "history_entry": "one-line summary of what changed, for the log",
    "last_updated_by": "YYYY-MM-DD | <agent> | <short topic>"
  },
  "tasks": {
    "add": [
      {"title": "...", "status": "pending", "priority": "medium",
       "notes": "...", "related_files": [], "updated_by": "..."}
    ],
    "update": [
      {"id": "T1", "status": "done", "notes": "...", "updated_by": "..."}
    ]
  },
  "index": {
    "descriptions": {"path/to/file": "short description"},
    "entrypoints": {"name": {"path": "...", "description": "..."}}
  },
  "project_rules_append": "- new rule text, already confirmed with the user"
}

expected_hashes: optional. If given, checked BEFORE anything else is
touched - if any listed file's current content doesn't match, nothing
is applied and the script exits with an error showing what mismatched.
Keys are paths relative to the project root, matching
.ai/manifests/.index_hashes.json's own keys (copy values from there,
or from this script's own prior output, to build this field).

history_entry: optional. Requires last_updated_by in the same payload.
Appended as a new, permanent, dated entry in .ai/HISTORY.md (newest
first, never edited after the fact) and mirrored into STATE.md's
"Recent Changes" section as the at-a-glance latest entry.
"""

import base64
import json
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AI_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = AI_DIR.parent
STATE_PATH = AI_DIR / "STATE.md"
HISTORY_PATH = AI_DIR / "HISTORY.md"
TASKS_PATH = AI_DIR / "tasks" / "state.json"
INDEX_PATH = AI_DIR / "manifests" / "index.json"
HASHES_PATH = AI_DIR / "manifests" / ".index_hashes.json"
PROJECT_RULES_PATH = AI_DIR / "PROJECT_RULES.md"

STATE_REL = STATE_PATH.relative_to(PROJECT_ROOT).as_posix()
TASKS_REL = TASKS_PATH.relative_to(PROJECT_ROOT).as_posix()
INDEX_REL = INDEX_PATH.relative_to(PROJECT_ROOT).as_posix()
PROJECT_RULES_REL = PROJECT_RULES_PATH.relative_to(PROJECT_ROOT).as_posix()

sys.path.insert(0, str(SCRIPT_DIR))
import generate_index  # noqa: E402

STATE_FIELD_MAP = {
    "project_goal": "## Project Goal",
    "current_status": "## Current Status",
    "resume_guidance": "## Resume Guidance",
    "notes": "## Notes",
}

VALID_STATUSES = {"pending", "in_progress", "blocked", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}

warnings = []
applied = []
touched = set()


def warn(msg):
    warnings.append(msg)
    print(f"WARNING: {msg}")


def load_payload():
    if len(sys.argv) > 1:
        try:
            raw = base64.b64decode(sys.argv[1]).decode("utf-8")
        except Exception as e:
            print(f"ERROR: could not base64-decode argument: {e}")
            sys.exit(1)
    else:
        raw = sys.stdin.read()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: payload is not valid JSON: {e}")
        sys.exit(1)


def check_expected_hashes(expected):
    """Abort before touching anything if any listed file's current hash
    doesn't match what the payload expects."""
    mismatches = []
    for rel_path, expected_hash in expected.items():
        actual_hash = generate_index.file_hash(PROJECT_ROOT / rel_path)
        if actual_hash != expected_hash:
            mismatches.append((rel_path, expected_hash, actual_hash))

    if not mismatches:
        return

    print("ERROR: file(s) changed since this payload was composed - nothing was applied.")
    for rel_path, expected_hash, actual_hash in mismatches:
        found = actual_hash if actual_hash is not None else "(file missing/unreadable)"
        print(f"  - {rel_path}: expected {expected_hash}, found {found}")
    print(
        "\nAsk for the current content of the affected file(s) - or the "
        "current .ai/manifests/.index_hashes.json - and regenerate the "
        "payload with fresh information."
    )
    sys.exit(1)


def replace_state_section(text, header, value, applied_label):
    marker = f"\n{header}\n"
    idx = text.find(marker)
    if idx == -1:
        warn(f"STATE.md section '{header}' not found; skipping '{applied_label}'.")
        return text
    start = idx + len(marker)
    next_header = text.find("\n## ", start)
    end = next_header if next_header != -1 else len(text)
    applied.append(f"state.{applied_label}")
    return text[:start] + value.rstrip() + "\n" + text[end:]


def update_history(entry_text, attribution):
    if not HISTORY_PATH.exists():
        warn("HISTORY.md not found; history entry not recorded.")
        return
    existing = HISTORY_PATH.read_text(encoding="utf-8")
    marker = "<!-- entries below -->\n"
    new_line = f"- {attribution}: {entry_text.strip()}\n"
    idx = existing.find(marker)
    if idx == -1:
        updated = existing.rstrip("\n") + "\n\n" + new_line
    else:
        insert_at = idx + len(marker)
        updated = existing[:insert_at] + new_line + existing[insert_at:]
    HISTORY_PATH.write_text(updated, encoding="utf-8")
    touched.add(HISTORY_PATH.relative_to(PROJECT_ROOT).as_posix())
    applied.append("history_entry")


def update_state(state_updates):
    if not STATE_PATH.exists():
        warn("STATE.md not found; skipping state updates.")
        return

    changing = [k for k in STATE_FIELD_MAP if k in state_updates]
    wants_history = "history_entry" in state_updates
    attribution = state_updates.get("last_updated_by")

    if (changing or wants_history) and not attribution:
        warn(
            "state fields were updated but 'last_updated_by' was not "
            "provided - STATE.md's attribution is now stale, and any "
            "history_entry was skipped. Include last_updated_by (format: "
            "YYYY-MM-DD | <agent> | <short topic>) in future payloads."
        )

    text = STATE_PATH.read_text(encoding="utf-8")

    if attribution:
        lines = text.split("\n")
        prefix = "last_updated_by:"
        for i, line in enumerate(lines):
            if line.startswith(prefix):
                lines[i] = f"{prefix} {attribution}"
                applied.append("state.last_updated_by")
                break
        text = "\n".join(lines)

    for key, header in STATE_FIELD_MAP.items():
        if key in state_updates:
            text = replace_state_section(text, header, state_updates[key], key)

    if wants_history:
        if attribution:
            entry_display = f"{attribution}: {state_updates['history_entry'].strip()}"
            text = replace_state_section(text, "## Recent Changes", entry_display, "recent_changes")
            update_history(state_updates["history_entry"], attribution)
        else:
            warn("history_entry given without last_updated_by; not recorded anywhere.")

    STATE_PATH.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    touched.add(STATE_REL)


def load_tasks():
    if not TASKS_PATH.exists():
        return None
    try:
        with open(TASKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        warn(f"could not read tasks/state.json: {e}")
        return None


def has_in_progress(tasks_data, exclude_id=None):
    return any(
        t.get("status") == "in_progress" and t.get("id") != exclude_id
        for t in tasks_data["tasks"]
    )


def update_tasks(tasks_updates):
    tasks_data = load_tasks()
    if tasks_data is None:
        warn("tasks/state.json unavailable; skipping task updates.")
        return

    today = date.today().isoformat()

    for new_task in tasks_updates.get("add", []):
        title = new_task.get("title")
        if not title:
            warn("skipped a task in 'add' with no title.")
            continue
        status = new_task.get("status", "pending")
        if status not in VALID_STATUSES:
            warn(f"task '{title}': invalid status '{status}', using 'pending'.")
            status = "pending"
        if status == "in_progress" and has_in_progress(tasks_data):
            warn(f"task '{title}': another task is already in_progress; "
                 f"adding as 'pending' instead.")
            status = "pending"
        priority = new_task.get("priority", "medium")
        if priority not in VALID_PRIORITIES:
            warn(f"task '{title}': invalid priority '{priority}', using 'medium'.")
            priority = "medium"
        updated_by = new_task.get("updated_by")
        if not updated_by:
            warn(f"task '{title}': no updated_by given; attribution will be blank.")

        task_id = f"T{tasks_data['next_id']}"
        tasks_data["next_id"] += 1
        tasks_data["tasks"].append({
            "id": task_id,
            "title": title,
            "status": status,
            "priority": priority,
            "created": today,
            "updated": today,
            "updated_by": updated_by or "",
            "notes": new_task.get("notes", ""),
            "related_files": new_task.get("related_files", []),
        })
        applied.append(f"tasks.add[{task_id}]")

    by_id = {t["id"]: t for t in tasks_data["tasks"]}
    for upd in tasks_updates.get("update", []):
        task_id = upd.get("id")
        if task_id not in by_id:
            warn(f"tasks.update: no task with id '{task_id}'; skipped.")
            continue
        task = by_id[task_id]
        new_status = upd.get("status")
        if new_status is not None:
            if new_status not in VALID_STATUSES:
                warn(f"task '{task_id}': invalid status '{new_status}'; skipped status change.")
            elif new_status == "in_progress" and has_in_progress(tasks_data, exclude_id=task_id):
                warn(f"task '{task_id}': another task is already in_progress; "
                     f"status change skipped.")
            else:
                task["status"] = new_status
        for field in ("priority", "notes", "related_files", "title"):
            if field in upd:
                task[field] = upd[field]
        if "updated_by" in upd:
            task["updated_by"] = upd["updated_by"]
        else:
            warn(f"task '{task_id}': updated with no updated_by given.")
        task["updated"] = today
        applied.append(f"tasks.update[{task_id}]")

    with open(TASKS_PATH, "w", encoding="utf-8") as f:
        json.dump(tasks_data, f, indent=2)
        f.write("\n")
    touched.add(TASKS_REL)


def update_index(index_updates):
    if not INDEX_PATH.exists():
        warn("manifests/index.json not found; skipping index updates.")
        return
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        warn(f"could not read index.json: {e}")
        return

    descriptions = index_updates.get("descriptions", {})
    if descriptions:
        by_path = {}
        for group in ("directories", "files"):
            for entry in index_data.get("structure", {}).get(group, []):
                by_path[entry["path"]] = entry
        for path, desc in descriptions.items():
            if path not in by_path:
                warn(f"index: path '{path}' not found in current index; skipped. "
                     f"(Only existing paths can get a description this way - "
                     f"structure changes come from the index script.)")
                continue
            by_path[path]["description"] = desc
            applied.append(f"index.descriptions[{path}]")

    entrypoints = index_updates.get("entrypoints", {})
    if entrypoints:
        index_data.setdefault("entrypoints", {}).update(entrypoints)
        applied.extend(f"index.entrypoints[{name}]" for name in entrypoints)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    touched.add(INDEX_REL)


def update_project_rules(note_text):
    existing = ""
    if PROJECT_RULES_PATH.exists():
        existing = PROJECT_RULES_PATH.read_text(encoding="utf-8")
    with open(PROJECT_RULES_PATH, "a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(note_text.rstrip() + "\n")
    touched.add(PROJECT_RULES_REL)
    applied.append("project_rules_append")


def refresh_hashes():
    """Keep .ai/manifests/.index_hashes.json current for whatever this
    run touched, merging into the existing map rather than replacing it
    (generate_index.py owns the full picture; this only patches the
    entries this run actually changed)."""
    if not touched:
        return
    existing = {}
    if HASHES_PATH.exists():
        try:
            with open(HASHES_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}
    new_hashes = {}
    for rel_path in touched:
        h = generate_index.file_hash(PROJECT_ROOT / rel_path)
        if h:
            existing[rel_path] = h
            new_hashes[rel_path] = h
    HASHES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HASHES_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return new_hashes


def main():
    payload = load_payload()
    if not isinstance(payload, dict):
        print("ERROR: payload must be a JSON object.")
        sys.exit(1)

    if "expected_hashes" in payload:
        check_expected_hashes(payload["expected_hashes"])

    if "state" in payload:
        update_state(payload["state"])
    if "tasks" in payload:
        update_tasks(payload["tasks"])
    if "index" in payload:
        update_index(payload["index"])
    if "project_rules_append" in payload:
        update_project_rules(payload["project_rules_append"])

    new_hashes = refresh_hashes()

    print()
    if applied:
        print(f"Applied {len(applied)} update(s):")
        for a in applied:
            print(f"  - {a}")
    else:
        print("Nothing was applied.")
    if warnings:
        print(f"{len(warnings)} warning(s) - see above.")
    if new_hashes:
        print("\nNew hashes (use as expected_hashes in your next payload):")
        for rel_path, h in sorted(new_hashes.items()):
            print(f"  {rel_path}: {h}")
    print(
        "\nNote: this does not rebuild manifests/index.json's file/folder "
        "structure. That happens automatically next time an index script runs."
    )


if __name__ == "__main__":
    sys.exit(main())
