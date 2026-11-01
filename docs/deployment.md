# Despliegue — PsyAI Connect

> **Resumen:** Cómo levantar el proyecto en desarrollo y producción usando Docker, variables de entorno, migraciones y diferencias clave entre `dev.py` y `prod.py`.  
> **Audiencia:** DevOps, desarrolladores que despliegan, leads técnicos.

---

## 1. Qué despliega este proyecto

PsyAI Connect se entrega como una aplicación Django contenedorizada. El despliegue estándar consta de dos servicios:

| Servicio | Imagen | Responsabilidad |
|----------|--------|-----------------|
| **app** | `python:3.12-slim` (build propio) | Servidor Django (runserver en dev / Waitress en prod) |
| **db** | `mysql:8.4` | Base de datos relacional MySQL 8 |

Ambos servicios comparten una red interna Docker (`psyai_net`) para que la app se conecte a la BD por el nombre de host `db`.

---

## 2. Requisitos previos

| Herramienta | Versión mínima | Uso |
|-------------|----------------|-----|
| Docker | 24+ | Containerización |
| Docker Compose | 2.20+ | Orquestación multi-contenedor |
| Git | 2.30+ | Control de versiones |
| Make / bash | — | Scripts de automatización (opcional) |

> **Recomendado:** tener una `SECRET_KEY` fuerte generada (ver sección 8) y, para producción, un dominio con certificados TLS válidos detrás de un reverse proxy (nginx, Traefik, AWS ALB, etc.).

---

## 3. Estructura de la carpeta `install/`

```
install/
├── Dockerfile             # Multi-stage: base → dev → prod
├── docker-compose.yml     # Desarrollo: app + MySQL con hot-reload
├── docker-compose.prod.yml# Override producción: prod target, waitress, no code volume
├── entrypoint.sh          # Espera a MySQL → migraciones → superuser (dev) → arranca servidor
└── .dockerignore          # Archivos excluidos de la imagen (.git, __pycache__, etc.)
```

---

## 4. `install/Dockerfile` — Multi-stage

El `Dockerfile` define tres etapas. Esto permite usar capas intermedias para cachear dependencias y entregar una imagen de producción sin herramientas de compilación.

```dockerfile
# ── Stage 1: base ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencias Python primero (caché de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: dev ──────────────────────────────────────────────────────────────
FROM base AS dev

ENV DJANGO_SETTINGS_MODULE=config.settings.dev \
    DEBUG=1

# El código se monta como volumen en docker-compose, no se copia aquí.
COPY install/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ── Stage 3: prod ─────────────────────────────────────────────────────────────
FROM base AS prod

ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    DEBUG=0

# Copia todo el código dentro de la imagen
COPY . .

# SECRET_KEY es obligatoria en tiempo de build para collectstatic
ARG SECRET_KEY=build-time-placeholder-replaced-at-runtime
ENV SECRET_KEY=${SECRET_KEY}
RUN python manage.py collectstatic --noinput

# Limpieza de archivos innecesarios en la imagen final
RUN rm -rf .git .pytest_cache __pycache__ \
    && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8000
COPY install/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "--threads=4", "config.wsgi:application"]
```

### Qué hace cada etapa

| Etapa | ¿Para qué sirve? | Característica clave |
|-------|------------------|----------------------|
| `base` | Instala dependencias del sistema y Python | Se reutiliza por `dev` y `prod` |
| `dev` | Imagen de desarrollo | Variables `DEBUG=1`, `runserver`, código montado por volumen (hot-reload) |
| `prod` | Imagen de producción | Código embebido en la imagen, `collectstatic` en build, `waitress` como servidor WSGI |

---

## 5. `install/entrypoint.sh` — Script de arranque

El entrypoint se ejecuta al iniciar el contenedor `app` y se encarga de dejar la base de datos lista antes de levantar el servidor:

```bash
#!/bin/bash
set -e

echo "==> PsyAI Connect — Entrypoint starting..."

# ── 1. Esperar a MySQL ────────────────────────────────────────────────────────
if [ -n "$DB_HOST" ] && [ "$DB_HOST" != "localhost" ]; then
    echo "==> Waiting for MySQL at $DB_HOST:${DB_PORT:-3306}..."
    until python - <<'PY'
import os, socket, sys
host = os.environ["DB_HOST"].strip()
port = int(os.environ.get("DB_PORT", "3306").strip())
try:
    socket.create_connection((host, port), timeout=2).close()
except Exception as e:
    print(f"    connect to {host}:{port} failed: {e}", file=sys.stderr)
    sys.exit(1)
PY
    do
        echo "    MySQL not ready yet, retrying in 2s..."
        sleep 2
    done
    echo "==> MySQL is ready!"
fi

# ── 2. Ejecutar migraciones ───────────────────────────────────────────────────
echo "==> Running migrations..."
python manage.py migrate --noinput 2>&1 || echo "WARNING: Migrations failed..."

# ── 3. Crear superuser si no existe (solo dev) ───────────────────────────────
if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.dev" ]; then
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

# ── 4. Arrancar el servidor ───────────────────────────────────────────────────
echo "==> Starting server..."
exec "$@"
```

### Flujo del entrypoint

1. **Espera a MySQL:** intenta abrir un socket TCP contra `DB_HOST:DB_PORT`. Reintenta cada 2 s hasta que tenga éxito.
2. **Migraciones:** ejecuta `python manage.py migrate --noinput` para poner al día el esquema.
3. **Superuser (dev únicamente):** crea `admin@psyai.com` / `Admin123` si no existe. En producción este paso se omite.
4. **Servidor:** ejecuta el comando definido en `CMD` (`runserver` en dev, `waitress-serve` en prod).

> **Permiso de ejecución:** el archivo ya tiene bit de ejecución en el repositorio. Si lo editas en Windows, asegúrate de que conserve los saltos de línea LF y el permiso `chmod +x`.

---

## 6. Desarrollo — `docker-compose.yml`

Este archivo levanta la pila completa para desarrollo local.

```yaml
services:
  # ── Django App ────────────────────────────────────────────────────────────
  app:
    build:
      context: ..
      dockerfile: install/Dockerfile
      target: dev
    container_name: psyai_app
    ports:
      - "${PORT:-8000}:8000"
    env_file:
      - ../.env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.dev
      - DEBUG=1
      - DB_HOST=db
      - DB_PORT=3306
      - DB_NAME=${DB_NAME:-psyai_connect}
      - DB_USER=${DB_USER:-psyai}
      - DB_PASSWORD=${DB_PASSWORD:-psyai_pass}
    volumes:
      # Hot-reload: el código del host se refleja al instante en el contenedor
      - ..:/app
      # Persistencia de documentos subidos entre reinicios
      - uploads_data:/app/static/uploads
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - psyai_net

  # ── MySQL 8 ───────────────────────────────────────────────────────────────
  db:
    image: mysql:8.4
    container_name: psyai_db
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:-rootpass}
      MYSQL_DATABASE: ${DB_NAME:-psyai_connect}
      MYSQL_USER: ${DB_USER:-psyai}
      MYSQL_PASSWORD: ${DB_PASSWORD:-psyai_pass}
    ports:
      - "3307:3306"   # Host:3307 → Contenedor:3306
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${DB_ROOT_PASSWORD:-rootpass}"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 30s
    restart: unless-stopped
    networks:
      - psyai_net

volumes:
  mysql_data:
    driver: local
  uploads_data:
    driver: local

networks:
  psyai_net:
    driver: bridge
```

### Levantar el entorno de desarrollo

Desde la raíz del proyecto:

```bash
# Construir y levantar en segundo plano
docker compose -f install/docker-compose.yml up -d --build

# Ver logs de la app
docker compose -f install/docker-compose.yml logs -f app

# Abrir shell dentro del contenedor app
docker compose -f install/docker-compose.yml exec app bash

# Ejecutar comandos de Django
docker compose -f install/docker-compose.yml exec app python manage.py migrate
docker compose -f install/docker-compose.yml exec app python manage.py createsuperuser

# Detener
docker compose -f install/docker-compose.yml down

# Detener y borrar volúmenes (¡borra la BD local!)
docker compose -f install/docker-compose.yml down -v
```

### Acceso en desarrollo

| Servicio | URL / Puerto | Notas |
|----------|--------------|-------|
| App Django | `http://localhost:8000` | `runserver` con hot-reload |
| MySQL | `localhost:3307` | Usuario `psyai`, BD `psyai_connect` |

---

## 7. Producción — `docker-compose.prod.yml`

Este archivo **sobrescribe** el servicio `app` para usar la etapa `prod` del `Dockerfile`, `Waitress` en lugar de `runserver`, y no monta el código como volumen (la imagen es inmutable).

```yaml
services:
  # ── Django App (Producción) ──────────────────────────────────────────────
  app:
    build:
      context: ..
      dockerfile: install/Dockerfile
      target: prod
      args:
        SECRET_KEY: ${SECRET_KEY:?Set SECRET_KEY in .env or environment}
    container_name: psyai_app_prod
    env_file:
      - ../.env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod
      - DEBUG=0
      - DB_HOST=db
      - DB_PORT=3306
      - DB_NAME=${DB_NAME:-psyai_connect}
      - DB_USER=${DB_USER:-psyai}
      - DB_PASSWORD=${DB_PASSWORD:-psyai_pass}
    # Código embebido en la imagen: no se monta volumen de código
    volumes:
      - uploads_data:/app/static/uploads
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - psyai_net

  # ── MySQL 8 (Producción) ─────────────────────────────────────────────────
  db:
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:?Set DB_ROOT_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME:-psyai_connect}
      MYSQL_USER: ${DB_USER:-psyai}
      MYSQL_PASSWORD: ${DB_PASSWORD:?Set DB_PASSWORD}
    # En producción se recomienda quitar el mapeo de puerto (solo red interna)
    ports: []
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped
    networks:
      - psyai_net

volumes:
  mysql_data:
    driver: local
  uploads_data:
    driver: local

networks:
  psyai_net:
    driver: bridge
```

### Levantar la pila de producción

Desde la raíz del proyecto:

```bash
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml up -d --build
```

### Puntos clave de producción

| Aspecto | Configuración |
|---------|---------------|
| Servidor WSGI | `waitress-serve` con 4 hilos |
| Código | Horneado en la imagen (no hay hot-reload) |
| BD MySQL | Puerto **no expuesto** al host (`ports: []`), accesible solo por la red interna `psyai_net` |
| `SECRET_KEY` | Obligatoria, pasada como `ARG` en el build |
| Archivos estáticos | `collectstatic` ejecutado durante el build de la imagen |
| Archivos subidos | Persisten en el volumen `uploads_data` |

> **Reverse proxy (recomendado):** el archivo `docker-compose.prod.yml` no incluye nginx por defecto. En producción expón la app detrás de un reverse proxy (nginx, Traefik, AWS ALB, Cloudflare Tunnel, etc.) que termine TLS, adelante `X-Forwarded-Proto` y `X-Forwarded-For`, y redirija tráfico al puerto `8000` del contenedor `app`.

---

## 8. Variables de entorno (`.env`)

Copia `.env.example` a `.env` en la raíz del proyecto y ajusta los valores. Nunca subas `.env` con secretos reales a control de versiones.

| Variable | Descripción | Ejemplo / Dev | Producción (requerida) |
|----------|-------------|---------------|------------------------|
| `SECRET_KEY` | Clave secreta Django | `dev-insecure-key-change-me` | **Obligatoria** (>50 chars, aleatoria) |
| `DEBUG` | Modo debug | `1` | `0` |
| `DJANGO_SETTINGS_MODULE` | Módulo de settings | `config.settings.dev` | `config.settings.prod` |
| `PORT` | Puerto app | `8000` | `8000` |
| `DB_HOST` | Host MySQL | `db` (Docker) | `db` (red interna) |
| `DB_PORT` | Puerto MySQL | `3306` | `3306` |
| `DB_NAME` | Nombre BD | `psyai_connect` | `psyai_connect` |
| `DB_USER` | Usuario BD | `psyai` | `psyai` |
| `DB_PASSWORD` | Password BD | `psyai_pass` | **Segura** |
| `DB_ROOT_PASSWORD` | Root MySQL (Docker) | `rootpass` | **Segura** |
| `ALLOWED_HOSTS` | Hosts permitidos | `*` | `tudominio.com,www.tudominio.com` |
| `CORS_ORIGINS` | Orígenes CORS | `http://localhost:5000` | `https://tudominio.com` |
| `CSRF_TRUSTED_ORIGINS` | CSRF trusted | `http://localhost:5000` | `https://tudominio.com` |
| `SESSION_COOKIE_SECURE` | Cookie segura | `False` | `True` |
| `CSRF_COOKIE_SECURE` | CSRF cookie segura | `False` | `True` |
| `CSRF_COOKIE_HTTPONLY` | CSRF HttpOnly | `False` | `True` |
| `SECURE_SSL_REDIRECT` | Forzar HTTPS | `False` | `True` |
| `SECURE_HSTS_SECONDS` | HSTS | `0` | `31536000` |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` | `smtp.gmail.com` |
| `EMAIL_PORT` | Puerto SMTP | `587` | `587` |
| `EMAIL_USE_TLS` | TLS | `True` | `True` |
| `EMAIL_HOST_USER` | Usuario SMTP | — | **Requerido** |
| `EMAIL_HOST_PASSWORD` | Pass SMTP | — | **Requerida** |
| `DEFAULT_FROM_EMAIL` | Remitente | — | `PsyAI Connect <noreply@tudominio.com>` |
| `GEMINI_API_KEY` | Key principal Gemini | — | **Requerida** |
| `GEMINI_API_KEYS` | Keys extra (rotación) | — | Opcional |
| `GEMINI_MODEL` | Modelo | `gemini-3.5-flash-lite` | `gemini-3.5-flash-lite` |
| `GEMINI_THINKING_LEVEL` | Nivel de razonamiento | `low` | `low` |
| `GEMINI_REQUEST_TIMEOUT_CONNECT` | Timeout de conexión (s) | `3` | `3` |
| `GEMINI_REQUEST_TIMEOUT_READ` | Timeout de lectura intento 1 (s) | `8` | `8` |
| `GEMINI_MIN_READ_TIMEOUT_SECONDS` | Read timeout mínimo garantizado (s) | `3` | `3` |
| `GEMINI_RETRIES` | Reintentos ante timeout/error de red | `2` | `2` |
| `GEMINI_RETRY_BASE_DELAY` | Retraso base entre reintentos (s) | `0.2` | `0.2` |
| `GEMINI_TOTAL_DEADLINE_SECONDS` | Presupuesto total Gemini (s) | `10` | `10` |
| `GEMINI_FALLBACK_MODEL` | Modelo de respaldo | `gemma-4-26b-a4b-it` | `gemma-4-26b-a4b-it` |
| `WOMPI_ENV` | `test` \| `prod` | `test` | `prod` |
| `WOMPI_PUBLIC_KEY` | Llave pública Wompi | — | **Requerida** |
| `WOMPI_PRIVATE_KEY` | Llave privada Wompi | — | **Requerida** |
| `WOMPI_INTEGRITY_SECRET` | Secreto integridad | — | **Requerida** |
| `WOMPI_EVENTS_SECRET` | Secreto eventos (webhook) | — | **Requerida** |
| `GOOGLE_CLIENT_ID` | OAuth Google | — | Opcional |
| `GOOGLE_CLIENT_SECRET` | Secret Google | — | Opcional |
| `SITE_URL` | URL base del sitio | `http://localhost:8000` | `https://tudominio.com` |

> **Generar `SECRET_KEY` segura:**
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(64))"
> ```

---

## 9. Diferencias clave `dev.py` vs `prod.py`

| Aspecto | `dev.py` | `prod.py` |
|---------|----------|-----------|
| `DEBUG` | `True` | `False` |
| `ALLOWED_HOSTS` | `["*"]` | De `ALLOWED_HOSTS` env |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | `False` (usa `CORS_ORIGINS`) |
| `SESSION_COOKIE_SECURE` | `False` | `True` |
| `CSRF_COOKIE_SECURE` | `False` | `True` |
| `CSRF_COOKIE_HTTPONLY` | `False` | `True` |
| `SECURE_SSL_REDIRECT` | `False` | `True` |
| `SECURE_HSTS_SECONDS` | `0` | `31536000` (1 año) |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` | `True` |
| `SECURE_HSTS_PRELOAD` | `False` | `True` |
| `EMAIL_BACKEND` | Console (si no credenciales) | SMTP real |
| Servidor | `runserver` (hot-reload) | `waitress` (producción) |

---

## 10. Checklist de despliegue a producción

- [ ] `SECRET_KEY` generada y en `.env` (`python -c "import secrets; print(secrets.token_urlsafe(64))"`)
- [ ] `DEBUG=False` en `.env` / `prod.py`
- [ ] `ALLOWED_HOSTS` y `CORS_ORIGINS` configurados con dominios reales
- [ ] `CSRF_TRUSTED_ORIGINS` = `CORS_ORIGINS`
- [ ] Certificados TLS válidos (Let's Encrypt o proveedor) → montar en `nginx/certs/`
- [ ] `nginx/prod.conf` configurado con `proxy_pass http://app:8000` y headers `X-Forwarded-Proto`
- [ ] `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` en `prod.py`
- [ ] `SECURE_PROXY_SSL_HEADER` configurado si hay proxy/load balancer
- [ ] `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_HTTPONLY=True`
- [ ] `SECURE_HSTS_SECONDS=31536000`, `INCLUDE_SUBDOMAINS=True`, `PRELOAD=True`
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF=True`, `X_FRAME_OPTIONS="DENY"`
- [ ] `CSP_ENABLED=True` (enforce, no Report-Only)
- [ ] Variables `WOMPI_*` y `GEMINI_API_KEY` configuradas
- [ ] `EMAIL_*` configuradas (SMTP real)
- [ ] `SITE_URL=https://tudominio.com`
- [ ] Migraciones aplicadas: `docker compose -f docker-compose.yml -f docker-compose.prod.yml exec app python manage.py migrate`
- [ ] `collectstatic` ejecutado (entrypoint lo hace)
- [ ] Superuser creado (entrypoint lo hace si no existe)
- [ ] Backups de BD programados (cron / RDS snapshots)
- [ ] Logs centralizados (stdout → Docker → Loki/ELK/Datadog)
- [ ] Healthchecks: `/api/session` o endpoint dedicado
- [ ] Monitoreo: CPU, RAM, disco, latencia p95, error rate

---

## 11. Comandos útiles

### Desarrollo

```bash
# Desarrollo
cd install
docker compose up -d --build          # Levantar
docker compose logs -f app             # Logs
docker compose exec app bash           # Shell en contenedor
docker compose exec app python manage.py shell
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
docker compose down                    # Detener
docker compose down -v                 # Detener + borrar volúmenes (BD)

# Producción
cd install
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f app
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec app python manage.py migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# Backup BD (desde host)
docker exec psyai_db mysqldump -u root -p"$DB_ROOT_PASSWORD" psyai_connect > backup_$(date +%F).sql

# Restore BD
docker exec -i psyai_db mysql -u root -p"$DB_ROOT_PASSWORD" psyai_connect < backup_2026-01-15.sql
```

---

## 12. Solución de problemas comunes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `app` reinicia en bucle | MySQL aún no está lista o credenciales incorrectas | Revisar `docker compose logs app` y verificar `DB_HOST`, `DB_PASSWORD`, `DB_ROOT_PASSWORD` |
| `collectstatic` falla en build de prod | `SECRET_KEY` no definida al construir | Exportar `SECRET_KEY` antes de `docker compose build` o definirla en `.env` |
| App no conecta a MySQL | `DB_HOST` apunta a `localhost` en lugar de `db` | En Docker, `DB_HOST` debe ser `db` (nombre del servicio) |
| Error 500 en producción | `DEBUG=0` oculta el detalle | Revisar logs: `docker compose ... logs app`; revisar `ALLOWED_HOSTS` |
| Archivos estáticos no cargan | `collectstatic` no se ejecutó | Rebuild de la imagen de producción (`up -d --build`) |
| Puerto MySQL no accesible desde host | En producción `ports: []` | Esto es intencional; accede a MySQL desde otro contenedor en la red `psyai_net` o usa un cliente dentro del contenedor `app` |

---

## Ver también

- [`config/settings/base.py`](../config/settings/base.py) — Settings base
- [`config/settings/dev.py`](../config/settings/dev.py) — Settings desarrollo
- [`config/settings/prod.py`](../config/settings/prod.py) — Settings producción
- [`install/Dockerfile`](../install/Dockerfile) — Imagen multi-stage
- [`install/docker-compose.yml`](../install/docker-compose.yml) — Compose desarrollo
- [`install/docker-compose.prod.yml`](../install/docker-compose.prod.yml) — Override producción
- [`install/entrypoint.sh`](../install/entrypoint.sh) — Script de arranque del contenedor
- [`security.md`](security.md) — Checklist de seguridad en producción
- [`api.md`](api.md) — Referencia completa de endpoints REST
- [`architecture.md`](architecture.md) — Arquitectura general del sistema
- [`chatbot-ai.md`](chatbot-ai.md) — Variables `GEMINI_API_KEY*`
- [`data-models.md`](data-models.md) — Modelos y relaciones de datos
- [`integrations.md`](integrations.md) — Integraciones externas