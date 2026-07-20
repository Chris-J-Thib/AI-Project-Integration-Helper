# Web AI Integration

How to connect various web-based AI tools to a project so they can read
`.ai/` (and the rest of the codebase) without needing local file or
execution access.

---

# GitHub Copilot (Full Functionality)

## Connect GitHub

Copilot Chat is native to GitHub - no separate connection or
authorization step beyond having (and being signed into) a GitHub
account. A free tier is available (no card required: 50 chat requests
+ 2,000 completions/month); paid plans (Pro, Pro+, Business,
Enterprise) raise those limits.

1.  Sign in to GitHub if not already.
2.  Go to [github.com/copilot](https://github.com/copilot), or open
    Copilot Chat from within a specific repo/issue/PR page to give it
    that context automatically.
3.  Ask your question, referencing the repo/file directly if needed.

## Capabilities

-   **Native Chat Access:** Available from any page on github.com,
    with context from whichever repo/issue/PR you're viewing.
-   **Free Tier:** Usable without a paid subscription or credit card.
-   **Coding Agent Dispatch:** Can assign work to the Copilot coding
    agent directly from chat. It works in the background and opens a
    draft pull request with its changes - real write access, not just
    read/suggest.

## Limitations

-   **Usage Caps on Free Tier:** 50 chat requests and 2,000
    completions/month; paid plans required beyond that.
-   **Agent Work Is Asynchronous:** Dispatched agent tasks run in the
    background and produce a draft PR for review, not an instant
    in-chat edit.
-   **Separate Desktop App for Deeper Work:** A more powerful native
    desktop app (macOS/Windows/Linux) exists for full agent-driven
    development, but that's outside the scope of web app usage covered
    here.

---

# ChatGPT GitHub Connector Setup (Full Functionality)

## Connect GitHub

1.  Open **ChatGPT → Settings → Apps**.
2.  Select **GitHub → Connect**.
3.  Sign in to GitHub if prompted.
4.  Install the **ChatGPT GitHub App**.
5.  Choose **Only selected repositories** (recommended).
6.  Authorize access.

> Organization repositories may require an administrator to approve the
> GitHub App.

## Repository Access

-   Grant access only to the repositories you want ChatGPT to use.
-   You can change repository access later from **Settings → Apps →
    GitHub**.

## Useful Custom Instructions

``` text
When I reference a repository by name, assume it belongs to my GitHub account unless I specify another owner.

If I say "pull repo" or give a specific Git related instruction do the following:
-Assume unless other wise specified that I am the owner of the repo ([Your-GitHub-Username])
-Immediately execute your backend GitHub/Codex connector tool to read the codebase
-Never state that you cannot access the link.
```

## How "pull repo" Works

Example:

    pull repo AI-Project-Intergration-Tool

With the custom instruction above, ChatGPT resolves:

-   Owner: `Chris-J-Thib`
-   Repository: `AI-Project-Intergration-Tool`

and reads the requested files directly through the GitHub connector.

## Security

-   Prefer **Only selected repositories**.
-   Review installed GitHub Apps periodically.
-   Revoke access when no longer needed.

---

# Claude GitHub Integration (Read-Only)

Available on **all plans, including Free**. Currently in beta.

## Connect GitHub

1. In a chat: click the **+** button in the lower-left corner, select
   **Add from GitHub**, then use the file browser to pick specific
   files/folders. This applies to that one conversation.
2. In a Project (for persistent access across conversations): click
   the **+** button in the Project's knowledge section, select
   **GitHub**, then browse or paste a repository URL and pick files.
3. If you're not authenticated with GitHub, you'll be redirected to
   authorize first.

There's no chat-command syntax for this (no `@GitHub`) - it's done
through the file browser before you send a message.

## Capabilities

- **Project-Level Context:** Syncs selected files/folders into a
  Project's knowledge so Claude can reference them across an entire
  conversation thread.
- **Code Analysis & Refactoring Suggestions:** Explains, debugs, and
  proposes changes based on the synced files.

## Limitations

- **Strictly Read-Only:** Cannot push, commit, or run git commands.
- **Manual Sync:** Not automatic - click "Sync now" to pull the latest
  version of your repo before relying on it being current.
- **Files Only:** Only file names and contents on a specific branch
  are synced. No commit history, PRs, issues, or other metadata.
- **Context Limits:** Repositories must fit within Claude's context
  window; very large repos will need selective file picking.

---

# Gemini GitHub Integration (Read-Only)

Desktop web only (not available on the Gemini mobile app). Requires
being signed in, 18+, and "Keep Activity" turned on. Work/school
Google accounts need a qualifying Workspace edition with admin-enabled
app access.

## Import a Repository

1. Go to [gemini.google.com](https://gemini.google.com) on a computer.
2. In the prompt box, click **Add file → More Uploads → Import code**.
3. Enter the GitHub repository or branch URL and click **Import**.
   (Private repos require linking your GitHub account first, which
   you'll be prompted to do.)
4. Enter your question and submit.

There's no separate "Extensions menu" step and no `@GitHub` chat
command - the app connects automatically the first time you import.

## Limits

- **One repository per chat**, up to **5,000 files** and **100 MB**
  total.
- **Static snapshot:** does not sync after import; re-import to update.

## What Gemini Can't Do (confirmed via Google's own docs)

- Retrieve commit history, pull requests, or other metadata.
- Read a repository just by pasting a GitHub URL into a prompt (must
  use the Import flow above).
- Write to a repository.

---

# Other Web Apps

The set of web AI tools with a direct, official GitHub integration is
still small. This list will grow as new methods appear or get
verified - open to workarounds if you've found one that works.

## Manual usage (no direct integration)

For any AI tool without a GitHub connector, this project still works
via direct upload: start by uploading `.ai/CONTRACT.md`, then upload
whatever else the AI asks for as it works through the read order
described there.
