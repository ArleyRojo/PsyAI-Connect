# Despliegue — PsyAI Connect

> **Resumen:** Cómo levantar el proyecto en desarrollo y producción usando Docker, variables de entorno, migraciones y diferencias clave entre `dev.py` y `prod.py`.  
> **Audiencia:** DevOps, desarrolladores que despliegan, leads técnicos.

---

## 1. Requisitos previos

| Herramienta | Versión mínima | Uso |
|-------------|----------------|-----|
| Docker | 24+ | Containerización |
| Docker Compose | 2.20+ | Orquestación multi-contenedor |
| Git | 2.30+ | Control de versiones |
| Make / bash | — | Scripts de automatización (opcional) |

---

## 2. Estructura de Docker

```
docker/
├── Dockerfile               # Multi-stage: builder → runtime (dev/prod)
├── docker-compose.yml       # Desarrollo: app + MySQL + phpMyAdmin (opcional)
├── docker-compose.prod.yml  # Override producción: waitress, sin hot-reload, logs JSON
├── entrypoint.sh            # Espera MySQL, migra, collectstatic, crea superuser, arranca
└── .dockerignore
```

---

## 3. `docker/Dockerfile` — Multi-stage

```dockerfile
# ---- Builder ----
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ---- Runtime (común) ----
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
```

> **Nota:** En `docker-compose.prod.yml` se sobrescribe el `CMD` para usar `waitress` en lugar de `runserver`.

---

## 4. `docker/entrypoint.sh`

```bash
#!/bin/bash
set -e

# 1. Espera a que MySQL acepte conexiones
until mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" --silent; do
  echo "Esperando MySQL..."
  sleep 2
done

# 2. Migraciones
python manage.py migrate --noinput

# 3. Archivos estáticos (solo en prod)
if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.prod" ]; then
    python manage.py collectstatic --noinput
fi

# 3. Superuser de prueba (solo si no existe)
python manage.py shell -c "
from apps.authentication.models import Register
if not Register.objects.filter(email='admin@psyai.com').exists():
    Register.objects.create_superuser('admin@psyai.com', 'Admin', 'Admin123')
"

# 4. Arranque
exec "$@"
```

> **Permisos:** `chmod +x docker/entrypoint.sh` en el repo.

---

## 5. Desarrollo — `docker-compose.yml`

```yaml
version: '3.8'

services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:-rootpass}
      MYSQL_DATABASE: ${DB_NAME:-psyai_connect}
      MYSQL_USER: ${DB_USER:-psyai}
      MYSQL_PASSWORD: ${DB_PASSWORD:-psyai_pass}
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3307:3306"   # Host:3307 → Contenedor:3306
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ..:/app  # Hot-reload: código montado
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.dev
      - DB_HOST=db
      - DB_PORT=3306
      - DB_NAME=${DB_NAME:-psyai_connect}
      - DB_USER=${DB_USER:-psyai}
      - DB_PASSWORD=${DB_PASSWORD:-psyai_pass}
      - DEBUG=True
      - SECRET_KEY=${SECRET_KEY:-dev-insecure-key-change-me}
    depends_on:
      db:
        condition: service_healthy

volumes:
  mysql_data:
  static_volume:
  media_volume:
```

**Levantar:**
```bash
cd docker
docker compose up -d --build
# App: http://localhost:8000
# MySQL: localhost:3307 (user: psyai, pass: psyai_pass)
```

**Logs:**
```bash
docker compose logs -f app
```

---

## 6. Producción — `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  db:
    # Misma config que dev, pero sin puerto expuesto en host
    # (solo red interna docker)
    deploy:
      resources:
        limits:
          memory: 1G

  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: >
      waitress-serve
      --port=8000
      --threads=8
      --connection-limit=1000
      config.wsgi:application
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      # NO montar código (imagen inmutable)
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod
      - DB_HOST=db
      - DB_PORT=3306
      # Variables sensibles SOLO en .env de prod
    depends_on:
      db:
        condition: service_healthy
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
      restart_policy:
        condition: on-failure
        max_attempts: 3

  nginx:  # Reverse proxy + SSL termination (recomendado)
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/prod.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - app

volumes:
  mysql_data:
  static_volume:
  media_volume:
```

**Levantar:**
```bash
cd docker
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 7. Variables de entorno (`.env`)

| Variable | Descripción | Dev default | Prod (requerida) |
|----------|-------------|-------------|------------------|
| `SECRET_KEY` | Clave secreta Django | `dev-insecure-key-change-me` | **Obligatoria** (>50 chars, aleatoria) |
| `DEBUG` | Modo debug | `True` | `False` |
| `DJANGO_SETTINGS_MODULE` | Settings module | `config.settings.dev` | `config.settings.prod` |
| `PORT` | Puerto app | `8000` | `8000` |
| `DB_HOST` | Host MySQL | `db` (Docker) | `db` (Docker) o IP RDS |
| `DB_PORT` | Puerto MySQL | `3306` | `3306` |
| `DB_NAME` | Nombre BD | `psyai_connect` | `psyai_connect` |
| `DB_USER` | Usuario BD | `psyai` | `psyai` |
| `DB_PASSWORD` | Password BD | `psyai_pass` | **Segura** |
| `DB_ROOT_PASSWORD` | Root MySQL (Docker) | `rootpass` | **Segura** |
| `ALLOWED_HOSTS` | Hosts permitidos | `*` | `tudominio.com,www.tudominio.com` |
| `CORS_ORIGINS` | Orígenes CORS | `http://localhost:5000,...` | `https://tudominio.com` |
| `CSRF_TRUSTED_ORIGINS` | CSRF trusted | `http://localhost:5000,...` | `https://tudominio.com` |
| `SESSION_COOKIE_SECURE` | Cookie segura | `False` | `True` |
| `CSRF_COOKIE_SECURE` | CSRF cookie segura | `False` | `True` |
| `CSRF_COOKIE_HTTPONLY` | CSRF HttpOnly | `False` (dev) | `True` |
| `SECURE_SSL_REDIRECT` | Forzar HTTPS | `False` | `True` |
| `SECURE_HSTS_SECONDS` | HSTS | `0` | `31536000` |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` | `smtp.gmail.com` |
| `EMAIL_PORT` | Puerto SMTP | `587` | `587` |
| `EMAIL_USE_TLS` | TLS | `True` | `True` |
| `EMAIL_HOST_USER` | Usuario SMTP | — | **Requerido** |
| `EMAIL_HOST_PASSWORD` | Pass SMTP | — | **Requerido** |
| `DEFAULT_FROM_EMAIL` | Remitente | — | `PsyAI Connect <noreply@tudominio.com>` |
| `GEMINI_API_KEY` | Key principal Gemini | — | **Requerida** |
| `GEMINI_API_KEYS` | Keys extra (rotación) | — | Opcional |
| `GEMINI_MODEL` | Modelo | `gemini-3.5-flash-lite` | `gemini-3.5-flash-lite` |
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

## 8. Diferencias clave `dev.py` vs `prod.py`

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
| `CSP_ENABLED` | `True` (Report-Only) | `True` (Enforce) |
| Servidor | `runserver` (hot-reload) | `waitress` (producción) |

---

## 9. Checklist de despliegue a producción

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

## 10. Comandos útiles

```bash
# Desarrollo
cd docker
docker compose up -d --build          # Levantar
docker compose logs -f app             # Logs
docker compose exec app bash           # Shell en contenedor
docker compose exec app python manage.py shell
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
docker compose down                    # Detener
docker compose down -v                 # Detener + borrar volúmenes (BD)

# Producción
cd docker
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

## Ver también

- [`config/settings/base.py`](../config/settings/base.py) — Settings base
- [`config/settings/prod.py`](../config/settings/prod.py) — Settings producción
- [`config/settings/dev.py`](../config/settings/dev.py) — Settings desarrollo
- [`docker/Dockerfile`](../docker/Dockerfile) — Imagen multi-stage
- [`docker/entrypoint.sh`](../docker/entrypoint.sh) — Script de arranque
- [`SEGURIDAD.md`](seguridad.md) — Checklist de seguridad en producción
- [`chatbot-ia.md`](chatbot-ia.md) — Variables `GEMINI_API_KEY*`
- [`pagos-facturacion.md`](pagos-facturacion.md) — Variables `WOMPI_*`
- [`whatsapp.md`](whatsapp.md) — Configuración de WhatsApp (Twilio)

---
## 11. Configuración de WhatsApp (Twilio)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `WHATSAPP_ENABLED` | Activa envío real (`true/1/yes` case‑insensitive) | `true` |
| `TWILIO_SID` | Account SID de Twilio | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_TOKEN` | Auth Token de Twilio | `your_auth_token` |
| `TWILIO_WHATSAPP_FROM` | Número remitente en formato `whatsapp:+...` | `whatsapp:+14155238886` |
| `TWILIO_WEBHOOK_URL` | URL pública exacta del webhook (debe coincidir con la configurada en Twilio) | `https://tudominio.com/api/whatsapp/webhook/` |
| `TWILIO_STATUS_CALLBACK_URL` *(opcional)* | URL para callbacks de estado (`delivered`, `failed`, …) | `https://tudominio.com/api/whatsapp/status/` |
| `TWILIO_TPL_RECORDATORIO` | Content SID de plantilla “recordatorio_cita” (aprobada en Meta) | `HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_TPL_CONFIRMACION` | Plantilla “confirmacion_cita” | `HX…` |
| `TWILIO_TPL_CANCELACION` | Plantilla “cancelacion_cita” | `HX…` |
| `TWILIO_TPL_MENSAJE_PRO` | Plantilla “mensaje_profesional” | `HX…` |

### Pasos para producción
1. **Cuenta Twilio** → *Messaging → Try it out → WhatsApp sandbox* para desarrollo. Cada número de prueba debe enviar `join <palabras>` al número del sandbox (`whatsapp:+14155238886`). La unión expira a 72 h.
2. **Producción** – Registrar un **WhatsApp Business Sender** (número propio, verificación Meta). Crear plantillas en Meta Business Manager → *Message Templates* → enviar a aprobación. Al aprobar, copiar el **Content SID** a las variables `TWILIO_TPL_*`.
3. **Webhook** – En Twilio Console → *Messaging → Settings → WhatsApp sandbox / Sender* → *When a message comes in* → `POST https://tudominio.com/api/whatsapp/webhook/`. Para exponer localmente usa **ngrok** y pon esa URL en `TWILIO_WEBHOOK_URL`.
4. **Status callback** (opcional) – En la misma pantalla *Status callback URL* pon `https://tudominio.com/api/whatsapp/status/`.
5. **Variables en `.env`** (nunca commitear):
   ```dotenv
   WHATSAPP_ENABLED=true
   TWILIO_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_TOKEN=your_auth_token
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   TWILIO_WEBHOOK_URL=https://tudominio.com/api/whatsapp/webhook/
   # TWILIO_STATUS_CALLBACK_URL=https://tudominio.com/api/whatsapp/status/
   TWILIO_TPL_RECORDATORIO=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_TPL_CONFIRMACION=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_TPL_CANCELACION=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_TPL_MENSAJE_PRO=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
6. **Probar**:  
   ```bash
   python manage.py probar_whatsapp +573001234567
   ```
   Debe mostrar `OK – Enviado (sid=SM…)` y el paciente recibe el WhatsApp.
7. **Opt‑out** – El usuario responde `STOP` / `BAJA` / `UNSUBSCRIBE`. El webhook valida la firma HMAC‑SHA1 (base64) y desactiva `whatsappConsentimiento` y pone `canalNotificacion=email`.
8. **Logs** – Cada envío queda en `Notificaciones` con `estado=enviado|fallido|simulado` y `providerMsgId` (SID real). El status callback actualiza a `delivered / failed / undelivered`.