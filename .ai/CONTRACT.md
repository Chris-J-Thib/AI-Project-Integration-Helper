# AI Contract

schema_version: 1.0

This file defines how an AI assistant should operate in this project. Treat
it as immutable unless the user explicitly requests contract changes.

## Read Order
1. .ai/CONTRACT.md (this file)
2. .ai/PROJECT_RULES.md, if present - rules specific to this project's
   codebase. These add to, and take priority over, this file's judgement
   calls (but not its safety-relevant rules).
3. .ai/STATE.md
4. .ai/tasks/state.json
5. .ai/manifests/index.json

## Connectivity Tiers
Your ability to act in this project falls into one of three tiers.
Determine which one applies at the start of every actual work session -
even within what looks like the same continuous conversation, since
tool/connector access can silently expire between messages (resuming a
chat after time away often finds a connector that worked last time no
longer does). If a tool call that previously worked suddenly fails,
re-classify immediately rather than assuming it was a one-off.

**Connected** - you have a tool that runs arbitrary commands/code in
this environment (a shell, a code-execution tool, an agentic coding
tool). Verify with something trivial and real, e.g. running
`git status` or listing a directory.
- Run the index/init/update scripts yourself.
- Edit any .ai file directly.
- Commit (and push, if a remote is configured) using real VCS commands.

**Restricted** - no execution tool, but you have a tool that can
create or modify a file in this repository directly - not just read
one (for example, a connected app's "commit" or "write file" action).
- You cannot run the index/init/update scripts - that needs real code
  execution against the real filesystem. Ask the user to run the
  appropriate one when needed.
- You CAN edit .ai files directly through that tool - STATE.md, tasks,
  index descriptions/entrypoints, PROJECT_RULES.md (with the user's
  explicit confirmation first, same as always). No need to relay
  through update.py - that exists specifically for the Disconnected
  tier below.
- Write and read are not always the same live connection: after
  writing, your in-context copy of a file may not auto-refresh. Re-sync
  before trusting it again, even if that means asking the user to
  trigger a manual sync. If your tool exposes file metadata, comparing
  it against .ai/manifests/.index_hashes.json can help confirm you're
  current.

**Disconnected** - neither of the above. This includes a read-only
sync (e.g. a GitHub integration that can browse files but not write
them) - rich context doesn't raise your tier if you can't persist
anything yourself.
- Ask the user to run the index/init scripts.
- For state/task/description/rules changes, use the Disconnected
  Update Workflow below.

## Disconnected Update Workflow
1. Compose a JSON payload describing the change(s) you want to make.
   The schema is documented at the top of .ai/scripts/update.py - it
   covers STATE.md fields, tasks, index descriptions/entrypoints, and
   (only with the user's explicit confirmation of the exact change,
   given in this conversation first) a PROJECT_RULES.md addition. If
   you're working from content that might be stale (it's been a while,
   or someone else may have touched the project since), include
   `expected_hashes` for the file(s) you're touching - the script
   checks these before applying anything and aborts cleanly, with
   nothing written, if they don't match, rather than silently
   overwriting a change it never saw.
2. Base64-encode the payload and give the user one ready-to-run
   command:
   - Linux/macOS: `.ai/scripts/update_linux.sh <base64>`
   - Windows: `.ai\scripts\update_windows.cmd <base64>`
3. Ask the user to run it in their own terminal, and to paste back the
   output if you need to confirm it worked - the script prints exactly
   what it applied and any warnings.
4. This does not rebuild the file/folder index - that happens
   automatically the next time an index or init script runs, which
   needs the user (or your own execution access, if you gain it later).

The update script applies a PROJECT_RULES.md change as given - it
doesn't re-confirm interactively, since the point is a single
non-interactive command. Confirming the exact wording with the user
happens in conversation, before you generate the command.

## Startup Check
- Check the `initialized` field in .ai/STATE.md before trusting anything
  else in .ai/.
- If `initialized: false`, or the field/file is missing or unreadable,
  treat the project as not yet set up:
  - If you're Connected, run the init script yourself:
    `.ai/scripts/init_linux.sh` (Linux/macOS) or
    `.ai\scripts\init_windows.cmd` (Windows).
  - Otherwise (Restricted or Disconnected), tell the user to run it,
    and wait.
  - Once init completes, restart from the top of the Read Order above -
    do not assume anything you read before init is still accurate.
- If `initialized: true`, proceed normally.

## Verify Before Trusting
STATE.md and tasks/state.json can be stale or wrong - written by a
session that ended abruptly, or by a Disconnected session working from
incomplete information. Before acting on them:

- Treat any task already marked `in_progress` as unconfirmed until you
  check it against reality - the session that set it may never have
  finished, or reported back, its work. Read what it actually touched
  (via `related_files`, if set) before continuing it or trusting it's
  genuinely still in progress.
- Cross-check Resume Guidance against .ai/manifests/index.json - if it
  references files or work the index shows no longer exists, don't act
  on it blindly. Note the discrepancy (via a history_entry) and ask the
  user if it's unclear.
- If you're Connected, generate_index.py prints warnings for multiple
  in_progress tasks and tasks referencing missing files - check its
  output, not just index.json's contents, after running it.

## Continuity Is the Priority
A session can end without warning - context limits, dropped connection,
closed tab - with no chance to leave a clean handoff note. Design every
action around that possibility:

- Update .ai/STATE.md continuously, not just at a natural stopping point
  or the end of a session. After each meaningful step, update "Current
  Status" and "Resume Guidance" so a fresh AI session could pick up
  cold with nothing lost.
- Record a `history_entry` for each meaningful step too, with
  `last_updated_by` (required for it to be recorded at all). This gets
  appended, dated and attributed, to the uncapped, permanent log in
  .ai/HISTORY.md, and mirrored into STATE.md's "Recent Changes" as an
  at-a-glance snapshot of the latest one. Never edit a past HISTORY.md
  entry - add a new one if something needs correcting. If you have
  execution access, running update.py yourself is the simplest way to
  do this correctly; if you're Restricted, follow the same pattern by
  hand (prepend to HISTORY.md, mirror into Recent Changes); if
  Disconnected, it's part of your update.py payload.
- Update .ai/tasks/state.json the same way - the moment a task's status
  changes, write it, don't batch updates for later.
- If .ai/STATE.md's `vcs_enabled` field is `true`, persist your work as
  you complete meaningful units of it - real commits (and a push, if a
  remote is configured) if you're Connected, or your connector's own
  write/commit action if you're Restricted. Don't wait to be asked.
  Prefer small, frequent commits/writes over large batched ones - each
  one is itself a save point.
- If you're Disconnected, you can't persist directly - use the
  Disconnected Update Workflow to at least keep STATE.md and
  tasks/state.json current, and ask the user to commit manually if
  that matters to them.
- Never plan to "update STATE.md at the end." There might not be one.

## Keeping the Index Fresh
- .ai/manifests/index.json is generated by .ai/scripts/generate_index.py
  (run via generate_index_linux.sh / generate_index_windows.cmd). It
  merges with the previous index: descriptions are kept for unchanged
  paths, carried over on detected renames (same content, new path), and
  dropped only when a path no longer exists.
- Run the appropriate index script yourself if you're Connected.
  Otherwise (Restricted or Disconnected - neither has real code
  execution), ask the user to run it; rebuilding the file/folder
  structure always requires an actual directory scan.
- New paths appear with an empty "description". As you come to
  understand what a file or folder does - by reading it, writing it, or
  reasoning about it - write a short description (roughly 5-10 words,
  as descriptive as it needs to be) back into index.json. Do this
  inline as understanding happens, not as a separate scheduled pass. If
  you're Connected or Restricted, write it directly; if Disconnected,
  include it in your next Disconnected Update Workflow payload.
- Fill in "entrypoints" the same way as you identify them (main scripts,
  build/run commands, primary modules) - these are high-value for a new
  session to read first.
- The index script owns index.json's structure (which paths are listed).
  Don't hand-edit structure; only edit description/entrypoints values.
- To exclude project-specific paths from the index beyond the script's
  defaults and .gitignore, add patterns to .ai/ignore rather than asking
  for the script itself to be changed.

## Core Rules
- Never assume a file exists or is current; verify against
  .ai/manifests/index.json, and re-run the index script if it might be
  stale.
- Only one task may have status `in_progress` at a time.
- Do not mark a task `done` until the work is actually complete and
  verified.
- Preserve task IDs; never renumber or reuse them, even after a task is
  removed. Use and increment `next_id` in tasks/state.json to assign the
  next one.
- Never delete or rename a .ai file unless explicitly instructed.
- Only edit .ai/PROJECT_RULES.md when the user explicitly confirms a
  rule addition or change - restate the exact change back to them before
  writing it.

## Task Schema
Each entry in .ai/tasks/state.json's `tasks` array:

| Field | Type | Notes |
|---|---|---|
| `id` | string | e.g. `"T1"`. Assigned from `next_id`, never reused. |
| `title` | string | Short task name. |
| `status` | string | One of: `pending`, `in_progress`, `blocked`, `done`. |
| `priority` | string | One of: `low`, `medium`, `high`. |
| `created` | string | Date created, `YYYY-MM-DD`. |
| `updated` | string | Date of last change, `YYYY-MM-DD`. |
| `updated_by` | string | Who last touched it, e.g. `"Claude"`. |
| `notes` | string | Current context, blockers, or next steps. |
| `related_files` | array | Relevant paths, matching index.json entries. |
