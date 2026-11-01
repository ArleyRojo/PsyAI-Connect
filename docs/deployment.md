# Despliegue — PsyAI Connect

> **Resumen:** Cómo levantar el proyecto en desarrollo y producción con Docker, las variables de entorno necesarias, las diferencias entre `dev.py` y `prod.py`, y los cuidados para un despliegue seguro.  
> **Audiencia:** desarrolladores, DevOps y leads técnicos.

---

## 1. Qué despliega este proyecto

PsyAI Connect se entrega como una aplicación Django 5 contenedorizada. El despliegue estándar consta de dos servicios:

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
| Docker Compose | 2.20+ | Orquestación de servicios |
| Git | 2.30+ | Clonar el repositorio |

> **Recomendado:** tener una `SECRET_KEY` fuerte generada (ver sección 7) y, para producción, un dominio con certificados TLS válidos detrás de un reverse proxy (nginx, Traefik, AWS ALB, etc.).

---

## 3. Estructura de la carpeta `install/`

```
install/
├── Dockerfile             # Imagen multi-stage: base → dev → prod
├── docker-compose.yml     # Desarrollo: app + MySQL con hot-reload
├── docker-compose.prod.yml# Override producción: target prod, waitress, sin volumen de código
├── entrypoint.sh          # Espera MySQL → migraciones → superuser (dev) → arranca servidor
└── .dockerignore          # Archivos excluidos de la imagen (.git, __pycache__, etc.)
```

---

## 4. `install/Dockerfile` — Imagen multi-stage

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

# Dependencias Python primero (cache de capas)
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

# Copia todo el código dentro de la imagen (inmutable en prod)
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

# 1. Esperar a que MySQL acepte conexiones (solo si DB_HOST no es localhost)
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

# 2. Ejecutar migraciones
echo "==> Running migrations..."
python manage.py migrate --noinput 2>&1 || echo "WARNING: Migrations failed..."

# 3. Crear superuser de prueba (solo en desarrollo)
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

# 4. Arrancar el servidor definido en CMD
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
| `DEBUG` | Modo depuración | `1` | `0` |
| `DJANGO_SETTINGS_MODULE` | Módulo de settings | `config.settings.dev` | `config.settings.prod` |
| `PORT` | Puerto de la app | `8000` | `8000` |
| `DB_HOST` | Host de MySQL | `db` | `db` (red interna) |
| `DB_PORT` | Puerto de MySQL | `3306` | `3306` |
| `DB_NAME` | Nombre de la BD | `psyai_connect` | `psyai_connect` |
| `DB_USER` | Usuario de la BD | `psyai` | `psyai` |
| `DB_PASSWORD` | Contraseña de la BD | `psyai_pass` | **Segura** |
| `DB_ROOT_PASSWORD` | Contraseña root MySQL (Docker) | `rootpass` | **Segura** |
| `ALLOWED_HOSTS` | Hosts permitidos | `*` | `tudominio.com,www.tudominio.com` |
| `CORS_ORIGINS` | Orígenes CORS permitidos | `http://localhost:5000` | `https://tudominio.com` |
| `CSRF_TRUSTED_ORIGINS` | Orígenes CSRF de confianza | `http://localhost:5000` | `https://tudominio.com` |
| `SESSION_COOKIE_SECURE` | Cookie de sesión solo HTTPS | `False` | `True` |
| `CSRF_COOKIE_SECURE` | Cookie CSRF solo HTTPS | `False` | `True` |
| `CSRF_COOKIE_HTTPONLY` | CSRF cookie HttpOnly | `False` | `True` |
| `SECURE_SSL_REDIRECT` | Forzar HTTPS | `False` | `True` |
| `SECURE_HSTS_SECONDS` | Tiempo HSTS | `0` | `31536000` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | HSTS subdominios | `False` | `True` |
| `SECURE_HSTS_PRELOAD` | HSTS preload | `False` | `True` |
| `EMAIL_HOST` | Servidor SMTP | `smtp.gmail.com` | `smtp.tuproveedor.com` |
| `EMAIL_PORT` | Puerto SMTP | `587` | `587` |
| `EMAIL_USE_TLS` | Usar TLS en SMTP | `True` | `True` |
| `EMAIL_HOST_USER` | Usuario SMTP | — | **Requerido** |
| `EMAIL_HOST_PASSWORD` | Contraseña SMTP | — | **Requerida** |
| `DEFAULT_FROM_EMAIL` | Remitente por defecto | — | `PsyAI Connect <noreply@tudominio.com>` |
| `GEMINI_API_KEY` | API key principal de Gemini | — | **Requerida** |
| `GEMINI_API_KEYS` | Keys extra para rotación | — | Opcional |
| `GEMINI_MODEL` | Modelo Gemini | `gemini-3.5-flash-lite` | `gemini-3.5-flash-lite` |
| `GEMINI_FALLBACK_MODEL` | Modelo de respaldo | `gemma-4-26b-a4b-it` | `gemma-4-26b-a4b-it` |
| `WOMPI_ENV` | Entorno Wompi (`test` \| `prod`) | `test` | `prod` |
| `WOMPI_PUBLIC_KEY` | Llave pública Wompi | — | **Requerida** |
| `WOMPI_PRIVATE_KEY` | Llave privada Wompi | — | **Requerida** |
| `WOMPI_INTEGRITY_SECRET` | Secreto de integridad Wompi | — | **Requerida** |
| `WOMPI_EVENTS_SECRET` | Secreto de eventos Wompi (webhook) | — | **Requerida** |
| `GOOGLE_CLIENT_ID` | OAuth Google | — | Opcional |
| `GOOGLE_CLIENT_SECRET` | Secreto OAuth Google | — | Opcional |
| `SITE_URL` | URL base del sitio | `http://localhost:8000` | `https://tudominio.com` |

### Generar una `SECRET_KEY` segura

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 9. Diferencias clave: `dev.py` vs `prod.py`

| Aspecto | `config/settings/dev.py` | `config/settings/prod.py` |
|---------|--------------------------|---------------------------|
| `DEBUG` | `True` | `False` |
| `ALLOWED_HOSTS` | `["*"]` | Desde variable `ALLOWED_HOSTS` |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | `False` (usa `CORS_ORIGINS`) |
| `SESSION_COOKIE_SECURE` | `False` | `True` |
| `CSRF_COOKIE_SECURE` | `False` | `True` |
| `CSRF_COOKIE_HTTPONLY` | `False` | `True` |
| `SECURE_SSL_REDIRECT` | `False` | `True` |
| `SECURE_HSTS_SECONDS` | `0` | `31536000` (1 año) |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` | `True` |
| `SECURE_HSTS_PRELOAD` | `False` | `True` |
| `EMAIL_BACKEND` | Consola (si no hay credenciales) | SMTP real |
| Servidor | `runserver` (hot-reload) | `waitress` (producción) |

---

## 10. Checklist antes de desplegar a producción

- [ ] `SECRET_KEY` generada y definida en `.env` o entorno de producción
- [ ] `DEBUG=0` y `DJANGO_SETTINGS_MODULE=config.settings.prod`
- [ ] `ALLOWED_HOSTS` y `CORS_ORIGINS` con dominios reales (no `*`)
- [ ] `CSRF_TRUSTED_ORIGINS` igual a `CORS_ORIGINS`
- [ ] Certificados TLS válidos montados en el reverse proxy
- [ ] Reverse proxy configurado con `proxy_pass http://app:8000` y headers `X-Forwarded-Proto`
- [ ] `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` si hay proxy/load balancer
- [ ] `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `CSRF_COOKIE_HTTPONLY=True`
- [ ] `SECURE_HSTS_SECONDS=31536000`, `INCLUDE_SUBDOMAINS=True`, `PRELOAD=True`
- [ ] Variables `WOMPI_*` y `GEMINI_API_KEY` configuradas
- [ ] Variables `EMAIL_*` configuradas con SMTP real
- [ ] `SITE_URL=https://tudominio.com`
- [ ] Migraciones aplicadas (`entrypoint.sh` las ejecuta automáticamente al iniciar)
- [ ] `collectstatic` ejecutado en el build de la imagen de producción
- [ ] Superuser creado (solo en dev; en prod crear manualmente si se necesita)
- [ ] Backups de MySQL programados (volumen `mysql_data` o snapshots de RDS)
- [ ] Logs centralizados (stdout de Docker → Loki/ELK/Datadog u otro)
- [ ] Healthcheck de MySQL funcionando (`mysqladmin ping`)

---

## 11. Comandos útiles

### Desarrollo

```bash
# Levantar
docker compose -f install/docker-compose.yml up -d --build

# Logs en tiempo real
docker compose -f install/docker-compose.yml logs -f app

# Shell dentro del contenedor app
docker compose -f install/docker-compose.yml exec app bash

# Shell de Django
docker compose -f install/docker-compose.yml exec app python manage.py shell

# Migraciones y superuser
docker compose -f install/docker-compose.yml exec app python manage.py migrate
docker compose -f install/docker-compose.yml exec app python manage.py createsuperuser

# Detener
docker compose -f install/docker-compose.yml down

# Detener y borrar volúmenes (borra la BD local)
docker compose -f install/docker-compose.yml down -v
```

### Producción

```bash
# Levantar con override de producción
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml up -d --build

# Logs de la app en producción
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml logs -f app

# Ejecutar migraciones manualmente (si es necesario)
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml exec app python manage.py migrate

# Detener
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml down
```

### Base de datos

```bash
# Backup desde el host (ajusta el nombre del contenedor si es distinto)
docker exec psyai_db mysqldump -u root -p"$DB_ROOT_PASSWORD" psyai_connect > backup_$(date +%F).sql

# Restaurar backup
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

## 13. Ver también

- [`config/settings/base.py`](../config/settings/base.py) — Settings base compartidos
- [`config/settings/dev.py`](../config/settings/dev.py) — Settings de desarrollo
- [`config/settings/prod.py`](../config/settings/prod.py) — Settings de producción
- [`install/Dockerfile`](../install/Dockerfile) — Imagen multi-stage
- [`install/docker-compose.yml`](../install/docker-compose.yml) — Compose de desarrollo
- [`install/docker-compose.prod.yml`](../install/docker-compose.prod.yml) — Override de producción
- [`install/entrypoint.sh`](../install/entrypoint.sh) — Script de arranque del contenedor
- [`security.md`](security.md) — Checklist de seguridad en producción
- [`api.md`](api.md) — Referencia de endpoints REST
- [`architecture.md`](architecture.md) — Arquitectura general del sistema
- [`chatbot-ai.md`](chatbot-ai.md) — Variables `GEMINI_API_KEY*`
- [`data-models.md`](data-models.md) — Modelos y relaciones de datos

---

## English Version

# Deployment — PsyAI Connect

> **Summary:** How to deploy the project in development and production using Docker, environment variables, migrations, and key differences between `dev.py` and `prod.py`.  
> **Audience:** DevOps, developers who deploy, technical leads.

---

## 1. What this project deploys / Qué despliega este proyecto

PsyAI Connect is delivered as a containerized Django 5 application. The standard deployment consists of two services:

| Service | Image | Responsibility |
|---|---|---|
| **app** | `python:3.12-slim` (own build) | Django server (`runserver` in dev / Waitress in prod) |
| **db** | `mysql:8.4` | Relational MySQL 8 database |

Both services share an internal Docker network (`psyai_net`) so the app connects to the DB using hostname `db`.

---

## 2. Prerequisites / Requisitos previos

| Tool | Minimum version | Use |
|---|---|---|
| Docker | 24+ | Containerization |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Git | 2.30+ | Version control |
| Make / bash | — | Automation scripts (optional) |

> **Recommended:** have a strong `SECRET_KEY` generated (see section 8) and, for production, a domain with valid TLS certificates behind a reverse proxy (nginx, Traefik, AWS ALB, Cloudflare Tunnel, etc.).

---

## 3. `install/` folder structure / Estructura de la carpeta `install/`

```
install/
├── Dockerfile             # Multi-stage: base → dev → prod
├── docker-compose.yml     # Development: app + MySQL with hot-reload
├── docker-compose.prod.yml# Production override: prod target, waitress, no code volume
├── entrypoint.sh          # Waits for MySQL → migrations → superuser (dev) → starts server
└── .dockerignore          # Files excluded from image (.git, __pycache__, etc.)
```

---

## 4. `install/Dockerfile` — Multi-stage image / `install/Dockerfile` — Imagen multi-stage

The `Dockerfile` defines three stages. This allows using intermediate layers to cache dependencies and deliver a production image without build tools.

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

# Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: dev ──────────────────────────────────────────────────────────────
FROM base AS dev

ENV DJANGO_SETTINGS_MODULE=config.settings.dev \
    DEBUG=1

# Code is mounted as a volume in docker-compose, not copied here.
COPY install/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ── Stage 3: prod ─────────────────────────────────────────────────────────────
FROM base AS prod

ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    DEBUG=0

# Copy full application code into the image
COPY . .

# SECRET_KEY is required at build time for collectstatic
ARG SECRET_KEY=build-time-placeholder-replaced-at-runtime
ENV SECRET_KEY=${SECRET_KEY}
RUN python manage.py collectstatic --noinput

# Remove unnecessary files from final image
RUN rm -rf .git .pytest_cache __pycache__ \
    && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8000
COPY install/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "--threads=4", "config.wsgi:application"]
```

### What each stage does / Qué hace cada etapa

| Stage | Purpose | Key feature |
|-------|---------|-------------|
| `base` | Installs system and Python dependencies | Reused by `dev` and `prod` |
| `dev` | Development image | `DEBUG=1`, `runserver`, code mounted by volume (hot-reload) |
| `prod` | Production image | Code embedded in image, `collectstatic` at build, `waitress` WSGI server |

---

## 5. `install/entrypoint.sh` — Startup script / `install/entrypoint.sh` — Script de arranque

The entrypoint runs when the `app` container starts and ensures the database is ready before starting the server:

```bash
#!/bin/bash
set -e

echo "==> PsyAI Connect — Entrypoint starting..."

# ── 1. Wait for MySQL ────────────────────────────────────────────────────────
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

# ── 2. Run migrations ────────────────────────────────────────────────────────
echo "==> Running migrations..."
python manage.py migrate --noinput 2>&1 || echo "WARNING: Migrations failed..."

# ── 3. Create superuser if it doesn't exist (dev only) ───────────────────────
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

# ── 4. Start the server ──────────────────────────────────────────────────────
echo "==> Starting server..."
exec "$@"
```

### Entrypoint flow / Flujo del entrypoint

1. **Waits for MySQL:** tries to open a TCP socket against `DB_HOST:DB_PORT`. Retries every 2 s until successful.
2. **Migrations:** runs `python manage.py migrate --noinput` to update the schema.
3. **Superuser (dev only):** creates `admin@psyai.com` / `Admin123` if it does not exist. In production this step is skipped.
4. **Server:** executes the command defined in `CMD` (`runserver` in dev, `waitress-serve` in prod).

> **Execution permission:** the file already has the execution bit in the repository. If you edit it on Windows, make sure it keeps LF line endings and the `chmod +x` permission.

---

## 6. Development — `docker-compose.yml` / Desarrollo — `docker-compose.yml`

This file brings up the complete stack for local development.

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
      # Hot-reload: host code is reflected instantly in the container
      - ..:/app
      # Persist uploaded documents between container restarts
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
      - "3307:3306"   # Host:3307 → Container:3306
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

### Start development environment / Levantar el entorno de desarrollo

From the project root:

```bash
# Build and start in background
docker compose -f install/docker-compose.yml up -d --build

# View app logs
docker compose -f install/docker-compose.yml logs -f app

# Open shell inside app container
docker compose -f install/docker-compose.yml exec app bash

# Run Django commands
docker compose -f install/docker-compose.yml exec app python manage.py migrate
docker compose -f install/docker-compose.yml exec app python manage.py createsuperuser

# Stop
docker compose -f install/docker-compose.yml down

# Stop and delete volumes (deletes local DB!)
docker compose -f install/docker-compose.yml down -v
```

### Development access / Acceso en desarrollo

| Service | URL / Port | Notes |
|---|---|---|
| Django App | `http://localhost:8000` | `runserver` with hot-reload |
| MySQL | `localhost:3307` | User `psyai`, DB `psyai_connect` |

---

## 7. Production — `docker-compose.prod.yml` / Producción — `docker-compose.prod.yml`

This file **overrides** the `app` service to use the `prod` stage of the `Dockerfile`, `Waitress` instead of `runserver`, and does not mount code as a volume (immutable image).

```yaml
services:
  # ── Django App (Production) ──────────────────────────────────────────────
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
    # Code embedded in image: no code volume mount
    volumes:
      - uploads_data:/app/static/uploads
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - psyai_net

  # ── MySQL 8 (Production) ─────────────────────────────────────────────────
  db:
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:?Set DB_ROOT_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME:-psyai_connect}
      MYSQL_USER: ${DB_USER:-psyai}
      MYSQL_PASSWORD: ${DB_PASSWORD:?Set DB_PASSWORD}
    # In production consider removing port mapping (internal only)
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

### Start production stack / Levantar la pila de producción

From the project root:

```bash
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml up -d --build
```

### Key production points / Puntos clave de producción

| Aspect | Configuration |
|---|---|
| WSGI server | `waitress-serve` with 4 threads |
| Code | Embedded in image (no hot-reload) |
| MySQL DB | Port **not exposed** to host (`ports: []`), accessible only via internal network `psyai_net` |
| `SECRET_KEY` | Mandatory, passed as `ARG` in build |
| Static files | `collectstatic` executed during image build |
| Uploaded files | Persist in volume `uploads_data` |

> **Reverse proxy (recommended):** `docker-compose.prod.yml` does not include nginx by default. In production expose the app behind a reverse proxy (nginx, Traefik, AWS ALB, Cloudflare Tunnel, etc.) that terminates TLS, forwards `X-Forwarded-Proto` and `X-Forwarded-For`, and routes traffic to port `8000` of container `app`.

---

## 8. Environment variables (`.env`) / Variables de entorno (`.env`)

Copy `.env.example` to `.env` in the project root and adjust values. Never commit `.env` with real secrets to version control.

| Variable | Description | Dev example | Production (required) |
|---|---|---|---|
| `SECRET_KEY` | Django secret key | `dev-insecure-key-change-me` | **Mandatory** (>50 chars, random) |
| `DEBUG` | Debug mode | `1` | `0` |
| `DJANGO_SETTINGS_MODULE` | Settings module | `config.settings.dev` | `config.settings.prod` |
| `PORT` | App port | `8000` | `8000` |
| `DB_HOST` | MySQL host | `db` (Docker) | `db` (internal network) |
| `DB_PORT` | MySQL port | `3306` | `3306` |
| `DB_NAME` | DB name | `psyai_connect` | `psyai_connect` |
| `DB_USER` | DB user | `psyai` | `psyai` |
| `DB_PASSWORD` | DB password | `psyai_pass` | **Secure** |
| `DB_ROOT_PASSWORD` | MySQL root password (Docker) | `rootpass` | **Secure** |
| `ALLOWED_HOSTS` | Allowed hosts | `*` | `tudominio.com,www.tudominio.com` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5000` | `https://tudominio.com` |
| `CSRF_TRUSTED_ORIGINS` | CSRF trusted origins | `http://localhost:5000` | `https://tudominio.com` |
| `SESSION_COOKIE_SECURE` | Session cookie HTTPS only | `False` | `True` |
| `CSRF_COOKIE_SECURE` | CSRF cookie HTTPS only | `False` | `True` |
| `CSRF_COOKIE_HTTPONLY` | CSRF cookie HttpOnly | `False` | `True` |
| `SECURE_SSL_REDIRECT` | Force HTTPS | `False` | `True` |
| `SECURE_HSTS_SECONDS` | HSTS time | `0` | `31536000` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | HSTS subdomains | `False` | `True` |
| `SECURE_HSTS_PRELOAD` | HSTS preload | `False` | `True` |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` | `smtp.tuproveedor.com` |
| `EMAIL_PORT` | SMTP port | `587` | `587` |
| `EMAIL_USE_TLS` | Use TLS in SMTP | `True` | `True` |
| `EMAIL_HOST_USER` | SMTP user | — | **Required** |
| `EMAIL_HOST_PASSWORD` | SMTP password | — | **Required** |
| `DEFAULT_FROM_EMAIL` | Default sender | — | `PsyAI Connect <noreply@tudominio.com>` |
| `GEMINI_API_KEY` | Main Gemini API key | — | **Required** |
| `GEMINI_API_KEYS` | Extra keys for rotation | — | Optional |
| `GEMINI_MODEL` | Gemini model | `gemini-3.5-flash-lite` | `gemini-3.5-flash-lite` |
| `GEMINI_FALLBACK_MODEL` | Fallback model | `gemma-4-26b-a4b-it` | `gemma-4-26b-a4b-it` |
| `WOMPI_ENV` | Wompi environment (`test` \| `prod`) | `test` | `prod` |
| `WOMPI_PUBLIC_KEY` | Wompi public key | — | **Required** |
| `WOMPI_PRIVATE_KEY` | Wompi private key | — | **Required** |
| `WOMPI_INTEGRITY_SECRET` | Wompi integrity secret | — | **Required** |
| `WOMPI_EVENTS_SECRET` | Wompi events secret (webhook) | — | **Required** |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | — | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | — | Optional |
| `SITE_URL` | Site base URL | `http://localhost:8000` | `https://tudominio.com` |

### Generate a secure `SECRET_KEY` / Generar una `SECRET_KEY` segura

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 9. Key differences `dev.py` vs `prod.py` / Diferencias clave `dev.py` vs `prod.py`

| Aspect | `config/settings/dev.py` | `config/settings/prod.py` |
|---|---|---|
| `DEBUG` | `True` | `False` |
| `ALLOWED_HOSTS` | `["*"]` | From `ALLOWED_HOSTS` env |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | `False` (uses `CORS_ORIGINS`) |
| `SESSION_COOKIE_SECURE` | `False` | `True` |
| `CSRF_COOKIE_SECURE` | `False` | `True` |
| `CSRF_COOKIE_HTTPONLY` | `False` | `True` |
| `SECURE_SSL_REDIRECT` | `False` | `True` |
| `SECURE_HSTS_SECONDS` | `0` | `31536000` (1 year) |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` | `True` |
| `SECURE_HSTS_PRELOAD` | `False` | `True` |
| `EMAIL_BACKEND` | Console (if no credentials) | Real SMTP |
| Server | `runserver` (hot-reload) | `waitress` (production) |

---

## 10. Production deployment checklist / Checklist de despliegue a producción

- [ ] `SECRET_KEY` generated and defined in `.env` or production environment
- [ ] `DEBUG=0` and `DJANGO_SETTINGS_MODULE=config.settings.prod`
- [ ] `ALLOWED_HOSTS` and `CORS_ORIGINS` with real domains (not `*`)
- [ ] `CSRF_TRUSTED_ORIGINS` equal to `CORS_ORIGINS`
- [ ] Valid TLS certificates mounted in reverse proxy
- [ ] Reverse proxy configured with `proxy_pass http://app:8000` and headers `X-Forwarded-Proto`
- [ ] `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` if behind proxy/load balancer
- [ ] `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `CSRF_COOKIE_HTTPONLY=True`
- [ ] `SECURE_HSTS_SECONDS=31536000`, `INCLUDE_SUBDOMAINS=True`, `PRELOAD=True`
- [ ] Variables `WOMPI_*` and `GEMINI_API_KEY` configured
- [ ] Variables `EMAIL_*` configured with real SMTP
- [ ] `SITE_URL=https://tudominio.com`
- [ ] Migrations applied (`entrypoint.sh` runs them automatically on container start)
- [ ] `collectstatic` executed in production image build
- [ ] Superuser created (only in dev; in prod create manually if needed)
- [ ] MySQL backups scheduled (volume `mysql_data` or RDS snapshots)
- [ ] Centralized logs (Docker stdout → Loki/ELK/Datadog or other)
- [ ] Healthchecks working (`mysqladmin ping`)

---

## 11. Useful commands / Comandos útiles

### Development / Desarrollo

```bash
# Start
docker compose -f install/docker-compose.yml up -d --build

# Real-time logs
docker compose -f install/docker-compose.yml logs -f app

# Shell inside app container
docker compose -f install/docker-compose.yml exec app bash

# Django shell
docker compose -f install/docker-compose.yml exec app python manage.py shell

# Migrations and superuser
docker compose -f install/docker-compose.yml exec app python manage.py migrate
docker compose -f install/docker-compose.yml exec app python manage.py createsuperuser

# Stop
docker compose -f install/docker-compose.yml down

# Stop and delete volumes (deletes local DB!)
docker compose -f install/docker-compose.yml down -v
```

### Production / Producción

```bash
# Start with production override
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml up -d --build

# App logs in production
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml logs -f app

# Run migrations manually (if needed)
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml exec app python manage.py migrate

# Stop
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml down
```

### Database / Base de datos

```bash
# Backup from host (adjust container name if different)
docker exec psyai_db mysqldump -u root -p"$DB_ROOT_PASSWORD" psyai_connect > backup_$(date +%F).sql

# Restore backup
docker exec -i psyai_db mysql -u root -p"$DB_ROOT_PASSWORD" psyai_connect < backup_2026-01-15.sql
```

---

## 12. Common issues / Solución de problemas comunes

| Symptom | Likely cause | Solution |
|---|---|---|
| `app` restarts in loop | MySQL not ready yet or wrong credentials | Check `docker compose logs app` and verify `DB_HOST`, `DB_PASSWORD`, `DB_ROOT_PASSWORD` |
| `collectstatic` fails in prod build | `SECRET_KEY` not defined at build time | Export `SECRET_KEY` before `docker compose build` or define it in `.env` |
| App cannot connect to MySQL | `DB_HOST` points to `localhost` instead of `db` | In Docker, `DB_HOST` must be `db` (service name) |
| 500 error in production | `DEBUG=0` hides details | Check logs: `docker compose ... logs app`; verify `ALLOWED_HOSTS` |
| Static files not loading | `collectstatic` not executed | Rebuild production image (`up -d --build`) |
| MySQL port not accessible from host | In production `ports: []` | Intentional; access MySQL from another container in network `psyai_net` or from inside `app` container |

---

## See also / Ver también

- [`config/settings/base.py`](../config/settings/base.py) — Base settings
- [`config/settings/dev.py`](../config/settings/dev.py) — Development settings
- [`config/settings/prod.py`](../config/settings/prod.py) — Production settings
- [`install/Dockerfile`](../install/Dockerfile) — Multi-stage image
- [`install/docker-compose.yml`](../install/docker-compose.yml) — Development compose
- [`install/docker-compose.prod.yml`](../install/docker-compose.prod.yml) — Production override
- [`install/entrypoint.sh`](../install/entrypoint.sh) — Container startup script
- [`security.md`](security.md) — Production security checklist
- [`api.md`](api.md) — Complete REST endpoints reference
- [`architecture.md`](architecture.md) — General system architecture
- [`chatbot-ai.md`](chatbot-ai.md) — `GEMINI_API_KEY*` variables
- [`data-models.md`](data-models.md) — Models and data relationships
- [`integrations.md`](integrations.md) — External integrations
