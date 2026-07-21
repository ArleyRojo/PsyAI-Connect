# ──────────────────────────────────────────────────────────────────────────────
# PsyAI Connect — Dockerfile
# Multi-stage: base → dev / prod
# ──────────────────────────────────────────────────────────────────────────────

# ── Stage 1: base ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by mysqlclient and general utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: dev ─────────────────────────────────────────────────────────────
FROM base AS dev

ENV DJANGO_SETTINGS_MODULE=config.settings.dev \
    DEBUG=1

# Code is mounted as a volume in docker-compose, not copied here.
# The entrypoint handles migrations + runserver.

EXPOSE 8000

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ── Stage 3: prod ────────────────────────────────────────────────────────────
FROM base AS prod

ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    DEBUG=0

# Copy the full application code into the image
COPY . .

# Collect static files at build time (SECRET_KEY needed by Django startup)
ARG SECRET_KEY=build-time-placeholder-replaced-at-runtime
ENV SECRET_KEY=${SECRET_KEY}
RUN python manage.py collectstatic --noinput

# Remove unnecessary files from the final image
RUN rm -rf .git .pytest_cache __pycache__ \
    && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8000

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "--threads=4", "config.wsgi:application"]
