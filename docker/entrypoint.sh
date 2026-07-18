#!/bin/bash
set -e

# ──────────────────────────────────────────────────────────────────────────────
# PsyAI Connect — Container Entrypoint
# 1. Wait for MySQL to be ready
# 2. Run migrations
# 3. Start the server (CMD)
# ──────────────────────────────────────────────────────────────────────────────

echo "==> PsyAI Connect — Entrypoint starting..."

# ── 1. Wait for MySQL ────────────────────────────────────────────────────────
# Only wait if DB_HOST is set (tests may use SQLite instead)
if [ -n "$DB_HOST" ] && [ "$DB_HOST" != "localhost" ]; then
    echo "==> Waiting for MySQL at $DB_HOST:${DB_PORT:-3306}..."
    until python -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('$DB_HOST', int('${DB_PORT:-3306}')))
    s.close()
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; do
        echo "    MySQL not ready yet, retrying in 2s..."
        sleep 2
    done
    echo "==> MySQL is ready!"
fi

# ── 2. Run migrations ────────────────────────────────────────────────────────
echo "==> Running migrations..."
python manage.py migrate --noinput 2>&1 || echo "WARNING: Migrations failed (maybe DB not ready, continuing anyway)"

# ── 3. Create superuser if it doesn't exist (dev only) ───────────────────────
if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.dev" ]; then
    python manage.py shell -c "
from apps.authentication.models import Register
if not Register.objects.filter(email='admin@psyai.com').exists():
    from apps.authentication.security import SecurityHelper
    u = Register(email='admin@psyai.com', nombre='Admin', rol='admin')
    u.contrasena = SecurityHelper.hash_password('Admin123')
    u.set_unusable_password()
    u.save()
    print('    Superuser created: admin@psyai.com / Admin123')
else:
    print('    Superuser already exists.')
" 2>/dev/null || true
fi

# ── 4. Start the server ──────────────────────────────────────────────────────
echo "==> Starting server..."
exec "$@"
