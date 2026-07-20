#!/bin/sh
# init_linux.sh - Ensures a usable Python 3.8+ is present (installing it
# if confirmed), then hands off to init.py for the rest of setup.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MIN_MAJOR=3
MIN_MINOR=8

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            ver_line=$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)
            if [ -n "$ver_line" ]; then
                major=$(echo "$ver_line" | cut -d. -f1)
                minor=$(echo "$ver_line" | cut -d. -f2)
                if [ "$major" -eq "$MIN_MAJOR" ] && [ "$minor" -ge "$MIN_MINOR" ]; then
                    echo "$candidate"
                    return 0
                fi
            fi
        fi
    done
    return 1
}

PYTHON_BIN=$(find_python)

detect_pkg_manager() {
    for pm in apt dnf yum apk pacman zypper; do
        if command -v "$pm" >/dev/null 2>&1; then
            echo "$pm"
            return 0
        fi
    done
    return 1
}

install_cmd_for() {
    case "$1" in
        apt) echo "sudo apt update && sudo apt install -y python3" ;;
        dnf) echo "sudo dnf install -y python3" ;;
        yum) echo "sudo yum install -y python3" ;;
        apk) echo "sudo apk add python3" ;;
        pacman) echo "sudo pacman -S --noconfirm python" ;;
        zypper) echo "sudo zypper install -y python3" ;;
    esac
}

show_more_info() {
    printf '%s\n' \
        "" \
        "Why Python is needed:" \
        "  This toolkit uses a Python script (generate_index.py) to scan the" \
        "  project and build/update .ai/manifests/index.json. That index is" \
        "  how an AI assistant quickly understands the project's structure" \
        "  without re-reading every file each session." \
        "" \
        "  The script also merges updates - it keeps existing file/folder" \
        "  descriptions and only adds or removes entries when files actually" \
        "  change, so context isn't lost between sessions." \
        "" \
        "  Python was chosen because it handles this reliably (correct JSON" \
        "  output, Unicode filenames, etc.) on both Linux and Windows, unlike" \
        "  plain shell/batch scripts." \
        ""
}

if [ -n "$PYTHON_BIN" ]; then
    echo "Found usable Python: $PYTHON_BIN ($("$PYTHON_BIN" -c 'import sys; print(sys.version.split()[0])'))"
    exec "$PYTHON_BIN" "$SCRIPT_DIR/init.py"
fi

echo "No usable Python 3.8+ found (Python 2 or missing does not count)."
echo "This project's AI tooling requires Python 3.8+ to build and maintain its index."
echo

PM=$(detect_pkg_manager)

while true; do
    if [ -n "$PM" ]; then
        echo "Options: [i]nstall using $PM, [m]ore info, [q]uit"
    else
        echo "Options: [m]ore info, [q]uit"
    fi
    printf "> "
    read -r choice
    case "$choice" in
        i|I)
            if [ -z "$PM" ]; then
                echo "No supported package manager detected; ignoring."
                continue
            fi
            cmd=$(install_cmd_for "$PM")
            echo "This will run: $cmd"
            printf "Proceed? [y/n] > "
            read -r confirm
            case "$confirm" in
                y|Y)
                    eval "$cmd"
                    PYTHON_BIN=$(find_python)
                    if [ -n "$PYTHON_BIN" ]; then
                        echo "Installed successfully: $PYTHON_BIN"
                        exec "$PYTHON_BIN" "$SCRIPT_DIR/init.py"
                    else
                        echo "Install ran but no usable Python 3.8+ was found afterward."
                        exit 1
                    fi
                    ;;
                *)
                    continue
                    ;;
            esac
            ;;
        m|M)
            show_more_info
            ;;
        q|Q)
            echo "Aborted. No dependencies were installed."
            exit 1
            ;;
        *)
            echo "Please enter i, m, or q."
            ;;
    esac
done
