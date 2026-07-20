> **AI:** Read `.ai/CONTRACT.md` next. It defines the read order for
> everything else in this folder and how to operate in this project.
> Do not act on this project before reading it.

# .ai - portable AI project context

Drop this folder into the root of any project to give an AI assistant
full, persistent context about the project: its structure, current
state, and in-progress work - without needing a long explanation at the
start of every session.

## Quick start

1. Copy the `.ai` folder into your project's root directory.
2. Run the setup script for your OS:
   - Linux/macOS: `.ai/scripts/init_linux.sh`
   - Windows: `.ai\scripts\init_windows.cmd`
3. Tell your AI assistant to read `.ai/CONTRACT.md`. If it's a chat
   tool without direct file access (e.g. a web chat), upload
   `.ai/CONTRACT.md` first, then whatever else it asks for as it works
   through the read order.

The init script checks for Python 3.8+ (installing it if you confirm),
optionally sets up git if this is a version-controlled project, and
builds the first project index.

## What's in .ai

| File | Purpose |
|---|---|
| `CONTRACT.md` | Operational rules for the AI - read order, how to keep state and the index up to date, when to commit |
| `PROJECT_RULES.md` | Optional, project-specific restrictions (blank by default) |
| `STATE.md` | Current project state - the handoff point between sessions |
| `HISTORY.md` | Uncapped, append-only log of changes across sessions |
| `tasks/state.json` | Active/pending task list |
| `manifests/index.json` | Generated map of the project's files and folders, with descriptions |
| `manifests/.index_hashes.json` | Generated, internal - content hashes, used for rename detection and to detect conflicting changes before an update is applied |
| `scripts/` | Setup, index-generation, and update scripts |

## Why

AI coding assistants generally lose all context between sessions. This
folder is a standing place for that context to live, so a new session -
even a completely different AI, in a different tool - can pick up where
the last one left off instead of starting from zero.
