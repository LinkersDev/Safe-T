#!/usr/bin/env bash
# =============================================================================
# run_tests.sh — run the SafeT test suite
#
# Usage:
#   bash scripts/run_tests.sh [app_label]
#
# Examples:
#   bash scripts/run_tests.sh                # run all tests
#   bash scripts/run_tests.sh apps.ledger    # run ledger tests only
#   bash scripts/run_tests.sh apps.risk      # run risk tests only
#
# The test settings use an in-memory SQLite database — no MySQL required.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

APP_LABEL="${1:-}"
SETTINGS="config.settings.test"

echo "==> SafeT Test Runner"
echo "    Settings : $SETTINGS  (in-memory SQLite)"
if [ -n "$APP_LABEL" ]; then
  echo "    Scope    : $APP_LABEL"
else
  echo "    Scope    : all apps"
fi
echo ""

python manage.py test $APP_LABEL \
  --settings="$SETTINGS" \
  --verbosity=2 \
  --failfast

echo ""
echo "==> All tests passed."
