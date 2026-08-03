#!/usr/bin/env bash
# Launcher for MD Viewer
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/md_viewer.py" "$@"
