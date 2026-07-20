#!/usr/bin/env python3
"""
init.py - One-time project setup.

Invoked by init_linux.sh / init_windows.cmd after they've confirmed a
usable Python 3.8+ is present. Asks whether this project uses git
(skipped if a .git directory already exists), installs git if needed
and confirmed, runs `git init` if appropriate, builds the first
project index, and marks .ai/STATE.md as initialized with the
project's actual git status.

Not meant to be run automatically more than once - the git question is
meant to be asked a single time. Re-running is harmless: if a .git
directory already exists (from a prior run or otherwise), the question
is skipped automatically.
"""

import platform
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STATE_PATH = SCRIPT_DIR.parent / "STATE.md"

sys.path.insert(0, str(SCRIPT_DIR))
import generate_index  # noqa: E402
import update  # noqa: E402

LINUX_PKG_MANAGERS = {
    "apt": "sudo apt update && sudo apt install -y git",
    "dnf": "sudo dnf install -y git",
    "yum": "sudo yum install -y git",
    "apk": "sudo apk add git",
    "pacman": "sudo pacman -S --noconfirm git",
    "zypper": "sudo zypper install -y git",
}
WINDOWS_PKG_MANAGERS = {
    "winget": "winget install -e --id Git.Git",
    "choco": "choco install -y git",
}


def ask_yes_no(prompt):
    while True:
        ans = input(f"{prompt} [y/n] > ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please enter y or n.")


def detect_pkg_manager():
    table = WINDOWS_PKG_MANAGERS if platform.system() == "Windows" else LINUX_PKG_MANAGERS
    for pm, cmd in table.items():
        if shutil.which(pm):
            return pm, cmd
    return None, None


def show_git_info():
    print()
    print("Why git is needed:")
    print("  Per .ai/CONTRACT.md, an AI assistant working in this project")
    print("  commits (and pushes, if a remote is configured) as it")
    print("  completes meaningful work, so progress isn't lost if a")
    print("  session ends unexpectedly. That requires git to be installed.")
    print()


def ensure_git_installed():
    found = shutil.which("git")
    if found:
        print(f"Found git: {found}")
        return True

    print("Git is not installed.")
    pm, install_cmd = detect_pkg_manager()

    while True:
        if pm:
            print(f"Options: [i]nstall using {pm}, [m]ore info, [q]uit")
        else:
            print("No supported package manager detected.")
            print("Options: [m]ore info, [q]uit")
        choice = input("> ").strip().lower()

        if choice == "i" and pm:
            print(f"This will run: {install_cmd}")
            if ask_yes_no("Proceed?"):
                subprocess.run(install_cmd, shell=True)
                if shutil.which("git"):
                    print("Installed successfully.")
                    return True
                print("Install ran but git still isn't available.")
                return False
        elif choice == "m":
            show_git_info()
        elif choice == "q":
            print("Skipping git setup.")
            return False
        else:
            valid = "i, m, or q" if pm else "m or q"
            print(f"Please enter {valid}.")


def setup_git():
    git_dir = PROJECT_ROOT / ".git"
    if git_dir.exists():
        print("Existing git repository detected; skipping the git question.")
        return

    if not ask_yes_no("Is this project version-controlled with git?"):
        return

    if not ensure_git_installed():
        print("Continuing without git.")
        return

    print("Initializing git repository...")
    subprocess.run(["git", "init"], cwd=str(PROJECT_ROOT))


def _set_state_field(lines, field, value):
    prefix = f"{field}:"
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = f"{prefix} {value}"
            return True
    return False


def mark_initialized():
    text = STATE_PATH.read_text(encoding="utf-8")
    lines = text.split("\n")
    _set_state_field(lines, "initialized", "true")
    is_git = (PROJECT_ROOT / ".git").exists()
    _set_state_field(lines, "vcs_enabled", "true" if is_git else "false")
    _set_state_field(lines, "project_name", PROJECT_ROOT.name)
    attribution = f"{date.today().isoformat()} | init.py | initial setup"
    _set_state_field(lines, "last_updated_by", attribution)
    text = "\n".join(lines)

    summary = "Project initialized."
    text = update.replace_state_section(
        text, "## Recent Changes", f"{attribution}: {summary}", "recent_changes"
    )

    STATE_PATH.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    update.touched.add(update.STATE_REL)
    update.update_history(summary, attribution)
    update.refresh_hashes()


def main():
    print(f"Initializing .ai for project: {PROJECT_ROOT.name}")
    setup_git()
    print("Building initial project index...")
    generate_index.main()
    mark_initialized()
    print("Setup complete. .ai/STATE.md marked as initialized.")


if __name__ == "__main__":
    sys.exit(main())
