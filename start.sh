#!/bin/bash
# CHEN-KIT v2.0 — Personal Kitchen Knowledge System
# Usage: ./start.sh
# Custom port: PORT=8080 ./start.sh

cd "$(dirname "$0")"
PORT=${PORT:-5555}
exec python3 dashboard.py
