#!/usr/bin/env bash
# =============================================================================
# setup_db.sh — initialise the SafeT MySQL database
#
# Prerequisites:
#   - MySQL 8+ is running
#   - .env is populated with DB_* variables
#   - Python environment is activated
#
# Usage:
#   bash scripts/setup_db.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

# Load .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

echo "==> Checking required environment variables..."
: "${DB_NAME:?'DB_NAME is not set in .env'}"
: "${DB_USER:?'DB_USER is not set in .env'}"
: "${DB_PASSWORD:?'DB_PASSWORD is not set in .env'}"
: "${DB_HOST:=${DB_HOST:-127.0.0.1}}"
: "${DB_PORT:=${DB_PORT:-3306}}"

echo "==> Creating database '${DB_NAME}' if it does not exist..."
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
EOF
echo "    Database ready."

echo "==> Running Django migrations..."
python manage.py migrate --settings=config.settings.base

echo "==> Creating default superuser (admin / +966500000000)..."
python manage.py shell --settings=config.settings.base <<'PYEOF'
from apps.users.models import User
from apps.users.constants import UserStatus
phone = "+966500000000"
if not User.objects.filter(phone_number=phone).exists():
    User.objects.create_superuser(
        phone_number=phone,
        password="Admin1234!",
        full_name="System Admin",
        status=UserStatus.ACTIVE,
    )
    print(f"  Superuser created: {phone} / Admin1234!")
else:
    print(f"  Superuser already exists: {phone}")
PYEOF

echo ""
echo "==> Database setup complete."
echo "    Run: bash scripts/run_server.sh"
