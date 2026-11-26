# Despliegue

## Contenedores

La imagen multi-stage usa `python:3.13-slim` e instala dependencias desde `requirements.txt`. PostgreSQL usa `postgres:16-alpine`. Compose está en `install/`; `.dockerignore` está en la raíz y `install/install.py` automatiza la preparación local.

### Dockerfile real

```dockerfile
FROM python:3.13-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
FROM base AS prod
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
COPY . .
RUN python manage.py collectstatic --noinput
RUN mkdir -p /app/static/uploads /app/media /app/backups && chown -R appuser:appuser /app
USER appuser
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 CMD curl -s http://localhost:8000/ > /dev/null || exit 1
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "--threads=32", "config.wsgi:application"]
```

El Dockerfile también define el stage `dev`, que ejecuta `install/entrypoint.sh` y `runserver`. En producción el entrypoint de la imagen inicia Waitress con 32 hilos y el usuario `appuser`.

### Compose

`install/docker-compose.yml` contiene `app`, `scheduler` y `db`. El servicio `scheduler` ejecuta `python manage.py programador`, espera a que `app` esté saludable y comparte los volúmenes de documentos y respaldos en desarrollo. `db` espera el healthcheck `pg_isready`.

`install/docker-compose.prod.yml` cambia app y scheduler al stage `prod`, no monta el código y exige `SECRET_KEY`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. PostgreSQL no publica puertos en producción. Ambos compose montan `uploads_data` y `backups_data` en el servicio app; desarrollo comparte `backups_data` con scheduler.

Los healthchecks de Compose consultan `http://localhost:8000/`; el `HEALTHCHECK` de la imagen también consulta `/`. La URL funcional de salud de Django es `/health/`.

### Comandos

```bash
docker compose -f install/docker-compose.yml up -d --build
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml up -d --build
docker compose -f install/docker-compose.yml logs -f scheduler
```

El usuario de demostración `admin@psyai.com` con contraseña `Admin123` se crea solo bajo `config.settings.dev`. No forma parte del checklist de producción.

## Variables de entorno

Las variables se leen principalmente en `config/settings/base.py`. `dev.py` cambia el correo a consola cuando no hay SMTP; `prod.py` valida `SECRET_KEY`. Cookies seguras, HSTS, redirección SSL, proxy SSL y `CSRF_TRUSTED_ORIGINS` se fijan en código (`prod.py` y `base.py`), no son variables configurables de producción.

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Clave de Django; producción exige al menos 50 caracteres y rechaza el valor inseguro. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión PostgreSQL. |
| `GEMINI_API_KEY`, `GEMINI_API_KEYS`, `GEMINI_MODEL`, `GEMINI_THINKING_LEVEL` | Acceso y parámetros del chatbot Gemini. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_TIMEOUT`, `DEFAULT_FROM_EMAIL`, `SITE_URL` | SMTP y URL usada en correos. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | OAuth de Google. |
| `PAGO_CUENTA_URL`, `PAGO_CUENTA_NOMBRE` | Datos generales del enlace de pago. |
| `CITA_MONTO_DEFAULT` | Monto predeterminado de cita. |
| `WHATSAPP_ENABLED`, `WHATSAPP_FALLBACK_TO_EMAIL`, `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_WHATSAPP_FROM` | Activación e integración de WhatsApp. |
| `TWILIO_TPL_RECORDATORIO`, `TWILIO_TPL_CONFIRMACION`, `TWILIO_TPL_CANCELACION`, `TWILIO_TPL_MENSAJE_PRO`, `TWILIO_TPL_FACTURA`, `TWILIO_TPL_CITA_GENERAL`, `TWILIO_TPL_NOTIFICACION_ADMIN` | Identificadores de plantillas Twilio. |
| `BACKUP_DIR` | Directorio de copias de seguridad. |
| `LEGAL_VERSION`, `EDAD_MINIMA_REGISTRO`, `RETENER_HISTORIA_CLINICA` | Parámetros legales, edad mínima y retención clínica. |
| `EMAIL_TIMEOUT` | Tiempo máximo de conexión de correo. |
| `MAX_UPLOAD_SIZE_MB`, `ALLOWED_UPLOAD_EXTENSIONS` | Límites de subida de archivos. |
| `ALLOW_PAGE_PREVIEW_WITHOUT_SESSION` | Vista previa de páginas; además requiere `DEBUG`. |
| `ALLOWED_HOSTS`, `CORS_ORIGINS` | Hosts y orígenes CORS permitidos. |

`REGISTER_RATE_LIMIT`, `LOGIN_RATE_LIMIT` y `PASSWORD_RECOVERY_RATE_LIMIT` aparecen en el ejemplo de entorno y settings, pero las vistas aplican límites mediante decoradores; esos valores no gobiernan los límites efectivos.

## Producción

```bash
docker compose -f install/docker-compose.yml -f install/docker-compose.prod.yml up -d --build
```

Configura una clave secreta segura, credenciales PostgreSQL, dominios permitidos, SMTP e integraciones necesarias. No se despliega Nginx ni certificados desde este repositorio.

## Ver también

- [Arquitectura](architecture.md)
- [Seguridad](security.md)
- [Testing](testing.md)