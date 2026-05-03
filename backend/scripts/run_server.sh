#!/usr/bin/env bash
# =============================================================================
# run_server.sh — start the SafeT development server
#
# Usage:
#   bash scripts/run_server.sh [port]
#
# Default port: 8000
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

PORT="${1:-8000}"
SETTINGS="${DJANGO_SETTINGS_MODULE:-config.settings.base}"

echo "==> SafeT Development Server"
echo "    Settings : $SETTINGS"
echo "    Port     : $PORT"
echo "    URL      : http://127.0.0.1:$PORT/"
echo "    Admin    : http://127.0.0.1:$PORT/admin/"
echo ""

# Apply any pending migrations automatically
echo "==> Checking for pending migrations..."
python manage.py migrate --settings="$SETTINGS" --run-syncdb

echo "==> Starting server..."
python manage.py runserver "0.0.0.0:${PORT}" --settings="$SETTINGS"
