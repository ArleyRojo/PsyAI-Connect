# ──────────────────────────────────────────────────────────────────────────────
# PsyAI Connect — Dockerfile
# Multi-stage: base → dev / prod
# ──────────────────────────────────────────────────────────────────────────────

# ── Stage 1: base ────────────────────────────────────────────────────────────
FROM python:3.13-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by psycopg (libpq) and PostgreSQL client tools (pg_isready)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    pkg-config \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: dev ─────────────────────────────────────────────────────────────
FROM base AS dev

ENV DJANGO_SETTINGS_MODULE=config.settings.dev \
    DEBUG=1

# Code is mounted as a volume in docker-compose, not copied here.
# The entrypoint handles migrations + runserver.

EXPOSE 8000

COPY install/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ── Stage 3: prod ────────────────────────────────────────────────────────────
FROM base AS prod

ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    DEBUG=0

# Create a non-root user for running the application (security best practice)
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy the full application code into the image
COPY . .

# Collect static files at build time (SECRET_KEY needed by Django startup)
ARG SECRET_KEY=build-time-placeholder-replaced-at-runtime
ENV SECRET_KEY=${SECRET_KEY}
RUN python manage.py collectstatic --noinput

# Remove unnecessary files from the final image
RUN rm -rf .git .pytest_cache __pycache__ \
    && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Ensure the app user owns the application directory (and uploads folder)
RUN mkdir -p /app/static/uploads /app/backups \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

# Healthcheck: verifica que el servidor responda en el puerto 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -s http://localhost:8000/ > /dev/null || exit 1

COPY install/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "--threads=4", "config.wsgi:application"]
