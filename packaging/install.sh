#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Detect Python
detect_python() {
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        echo "$VIRTUAL_ENV/bin/python"
        return
    fi
    for candidate in python3 python; do
        if command -v "$candidate" &>/dev/null; then
            if "$candidate" -c "import helmd" &>/dev/null; then
                command -v "$candidate"
                return
            fi
        fi
    done
    echo "ERROR: No Python interpreter found with helmd installed." >&2
    echo "Activate your virtual environment or install helmd first." >&2
    exit 1
}

PYTHON_EXECUTABLE="$(detect_python)"
echo "Using Python: $PYTHON_EXECUTABLE"

# 2. Detect OS
OS="$(uname -s)"

# 3. Create log directory
if [[ "$OS" == "Darwin" ]]; then
    LOG_DIR="$HOME/Library/Application Support/helm/logs"
else
    LOG_DIR="$HOME/.config/helm/logs"
fi
mkdir -p "$LOG_DIR"

# 4. Install service
if [[ "$OS" == "Darwin" ]]; then
    PLIST_SRC="$SCRIPT_DIR/launchd/com.media-os.helmd.plist"
    PLIST_DST="$HOME/Library/LaunchAgents/com.media-os.helmd.plist"

    mkdir -p "$HOME/Library/LaunchAgents"
    sed \
        -e "s|{{PYTHON_EXECUTABLE}}|$PYTHON_EXECUTABLE|g" \
        -e "s|{{HOME}}|$HOME|g" \
        "$PLIST_SRC" > "$PLIST_DST"

    launchctl unload "$PLIST_DST" 2>/dev/null || true
    launchctl load -w "$PLIST_DST"

    echo "helmd installed as launchd agent: $PLIST_DST"
    echo "Logs: $LOG_DIR"

elif [[ "$OS" == "Linux" ]]; then
    SERVICE_SRC="$SCRIPT_DIR/systemd/helmd.service"
    SERVICE_DST="$HOME/.config/systemd/user/helmd.service"

    mkdir -p "$HOME/.config/systemd/user"
    sed \
        -e "s|{{PYTHON_EXECUTABLE}}|$PYTHON_EXECUTABLE|g" \
        "$SERVICE_SRC" > "$SERVICE_DST"

    systemctl --user daemon-reload
    systemctl --user enable --now helmd

    echo "helmd installed as systemd user service: $SERVICE_DST"
    echo "Logs: $LOG_DIR"

else
    echo "ERROR: Unsupported OS: $OS" >&2
    exit 1
fi

echo "Done. helmd is running."
