#!/usr/bin/env bash
#
# Install the misp-galaxy-editor as a systemd --user service.
#
# This renders systemd/misp-galaxy-editor.service.template with the current
# install path and drops the result into ~/.config/systemd/user/. The service
# runs gunicorn against app:app, survives SSH disconnects, and restarts on
# failure.
#
# Usage:
#   ./install-service.sh                  # install with defaults
#   PORT=5051 HOST=0.0.0.0 ./install-service.sh
#   WORKERS=4 ./install-service.sh
#
# After install:
#   systemctl --user start  misp-galaxy-editor
#   systemctl --user status misp-galaxy-editor
#   journalctl --user -u misp-galaxy-editor -f
#
# To have the service keep running after you log out:
#   sudo loginctl enable-linger "$USER"
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="misp-galaxy-editor"
TEMPLATE="$SCRIPT_DIR/systemd/${SERVICE_NAME}.service.template"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_PATH="$UNIT_DIR/${SERVICE_NAME}.service"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5051}"
WORKERS="${WORKERS:-2}"

if [ ! -f "$TEMPLATE" ]; then
    echo "ERROR: service template not found at $TEMPLATE" >&2
    exit 1
fi

# Make sure the venv exists and gunicorn is installed before we hand off to
# systemd — otherwise the first start will just fail and confuse the user.
if [ ! -x "$SCRIPT_DIR/venv/bin/gunicorn" ]; then
    echo "Setting up virtualenv and installing dependencies..."
    if [ ! -d "$SCRIPT_DIR/venv" ]; then
        python3 -m venv "$SCRIPT_DIR/venv"
    fi
    "$SCRIPT_DIR/venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
fi

mkdir -p "$UNIT_DIR"

sed \
    -e "s|@INSTALL_DIR@|$SCRIPT_DIR|g" \
    -e "s|@HOST@|$HOST|g" \
    -e "s|@PORT@|$PORT|g" \
    -e "s|@WORKERS@|$WORKERS|g" \
    "$TEMPLATE" > "$UNIT_PATH"

echo "Wrote $UNIT_PATH"

systemctl --user daemon-reload
systemctl --user enable "${SERVICE_NAME}.service"
systemctl --user restart "${SERVICE_NAME}.service"

echo
echo "Service installed and started. Useful commands:"
echo "  systemctl --user status  $SERVICE_NAME"
echo "  systemctl --user restart $SERVICE_NAME"
echo "  systemctl --user stop    $SERVICE_NAME"
echo "  journalctl --user -u $SERVICE_NAME -f"
echo
echo "To keep the service running after logout, run once:"
echo "  sudo loginctl enable-linger \"$USER\""
