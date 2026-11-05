#!/bin/bash
set -e

# ──────────────────────────────────────────────────────────────────────────────
# PsyAI Connect — Container Entrypoint (PostgreSQL 16)
# 1. Espera a que PostgreSQL esté listo (pg_isready)
# 2. Crea la base de datos si no existe
# 3. Ejecuta migraciones
# 4. Crea el superuser demo (solo dev)
# 5. Arranca el servidor (CMD)
# ──────────────────────────────────────────────────────────────────────────────

echo "==> PsyAI Connect — Entrypoint starting (PostgreSQL)..."

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_NAME="${DB_NAME:-psyai_connect}"

# En producción, SECRET_KEY es obligatorio
if [ "${DJANGO_SETTINGS_MODULE}" = "config.settings.prod" ] && [ -z "${SECRET_KEY:-}" ]; then
    echo "ERROR: SECRET_KEY is required in production" >&2
    exit 1
fi

# ── 1. Wait for PostgreSQL ────────────────────────────────────────────────────
# Solo se espera si DB_HOST está definido y no es localhost (tests pueden usar SQLite).
if [ -n "$DB_HOST" ] && [ "$DB_HOST" != "localhost" ]; then
    echo "==> Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
        echo "    PostgreSQL not ready yet, retrying in 2s..."
        sleep 2
    done
    echo "==> PostgreSQL is ready!"
fi

# ── 2. Create the database if it does not exist ───────────────────────────────
if [ -n "$DB_HOST" ] && [ "$DB_HOST" != "localhost" ]; then
    echo "==> Ensuring database $DB_NAME exists..."
    # Conectarse a la BD 'postgres' (siempre existe) y crear la objetivo si falta.
    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME"
        echo "    Database $DB_NAME created."
    else
        echo "    Database $DB_NAME already exists."
    fi
fi

# ── 3. Run migrations ─────────────────────────────────────────────────────────
echo "==> Running migrations..."
python manage.py migrate --noinput

# ── 4. Create superuser if it doesn't exist (dev only) ────────────────────────
if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.dev" ]; then
    echo "==> Ensuring demo superuser exists..."
    python manage.py shell -c "
from apps.authentication.models import Register
from apps.authentication.security import SecurityHelper
if not Register.objects.filter(email='admin@psyai.com').exists():
    u = Register(email='admin@psyai.com', nombre='Admin', rol='admin')
    u.contrasena = SecurityHelper.hash_password('Admin123')
    u.set_unusable_password()
    u.save()
    print('    Superuser created: admin@psyai.com / Admin123')
else:
    print('    Superuser already exists.')
" 2>/dev/null || true
fi

# ── 5. Start the server ───────────────────────────────────────────────────────
echo "==> Starting server..."
exec "$@"
