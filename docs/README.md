# Documentación Técnica de PsyAI Connect

> **Índice de la carpeta `docs/`** — Aquí vive toda la documentación técnica detallada del proyecto.  
> El archivo `README.md` en la **raíz del repositorio** sigue siendo la puerta de entrada general (visión general, instalación rápida, stack tecnológico). Todo lo demás — incluida la referencia completa de la API — se encuentra en esta carpeta.

---

## Tabla de contenidos

| Documento | Descripción |
|-----------|-------------|
| [`api.md`](api.md) | **Referencia completa de endpoints REST** (`/api/...`) por app: autenticación, agenda, facturación, pacientes, profesionales, documentos, chatbot, admin. Incluye método HTTP, autenticación requerida y roles permitidos. |
| [`seguridad.md`](seguridad.md) | **Estado de seguridad del sistema**: capas preexistentes (autenticación, rate limiting, RBAC, HMAC Wompi, validación de archivos, throttling, CORS, HSTS) y las 6 capas agregadas en la iteración de hardening (CSRF real, rotación de sesión, enlace de recuperación HTTPS, verificación de email, CSP, 2FA/TOTP). |
| [`modelos-de-datos.md`](modelos-de-datos.md) | **Modelo de datos del proyecto**: modelos principales por app (`Register`, `PerfilPaciente`, `PerfilProfesional`, `Citas`, `Facturas`, `Documentos`, `ConversacionesChatbot`, etc.), campos clave, relaciones (FK, M2M) y diagrama entidad-relación en Mermaid. |
| [`roles-y-permisos.md`](roles-y-permisos.md) | **Roles y permisos**: tres roles (`paciente`, `profesional`, `admin`), qué pantallas ve cada uno (`templates/patient/`, `templates/professional/`, `templates/admin/`), clases de permiso DRF (`IsAuthenticatedDRF`, `IsPaciente`, `IsProfesional`, `IsAdmin`, etc.), tabla rol × funcionalidad. |
| [`frontend.md`](frontend.md) | **Organización del frontend**: estructura de `static/js/` (`core/shared/`, `modules/<rol>/`, `base/`), carga de scripts en templates (`templates/base/partials/scripts.html`), sistema de notificaciones `PsyAIAlerts`, tema claro/oscuro (`theme.js`, variables CSS en `theme.css`), convenciones de nombres. |
| [`chatbot-ia.md`](chatbot-ia.md) | **Chatbot con Google Gemini**: flujo `enviarMensaje` → `/api/chatbot/enviar` → `services.py`, rotación de API keys, detección de riesgo emocional (alto/medio/bajo) en `services.py`, plantilla de alerta `alerta_riesgo.html`. Aclara que es triaje/apoyo, no sustituto de atención profesional. |
| [`pagos-facturacion.md`](pagos-facturacion.md) | **Flujo de facturación y pagos**: creación de facturas (`POST /api/facturas`), inicio de pago Wompi (`iniciar-pago`, hash de integridad), confirmación frontend (`agendaquotes.js`), webhook autoritativo `WebhookWompiView` con verificación HMAC. Diferencia entre confirmación frontend (UX) y webhook (fuente de verdad). |
| [`despliegue.md`](despliegue.md) | **Despliegue con Docker**: `Dockerfile` multi-stage, `docker-compose.yml` (dev) vs `docker-compose.prod.yml` (prod), `entrypoint.sh`, variables de entorno (`.env`, `config/settings/base.py` y `prod.py`), diferencias clave `dev.py` vs `prod.py`. |
| [`testing.md`](testing.md) | **Testing**: organización (`pytest.ini`, `conftest.py` raíz, `apps/*/tests/` con `test_repositories.py`, `test_services.py`, `test_views.py`), ejecución (`pytest`, cobertura con `pytest-cov`), convención de capas (repository/service/view) y tests de integración. |
| [`modelos-de-datos.md`](modelos-de-datos.md) | **Modelos de datos**: detalle de modelos por app (`Register`, `PerfilPaciente`, `PerfilProfesional`, `Citas`, `Facturas`, `Documentos`, `ConversacionesChatbot`, etc.), campos clave, relaciones y diagrama entidad-relación Mermaid. |
| [`roles-y-permisos.md`](roles-y-permisos.md) | **Roles y permisos**: detalle de los tres roles, pantallas, clases de permiso DRF, tabla rol × funcionalidad. |
| [`frontend.md`](frontend.md) | **Frontend**: organización JS, carga de scripts, `PsyAIAlerts`, tema claro/oscuro, convenciones. |
| [`chatbot-ia.md`](chatbot-ia.md) | **Chatbot IA**: flujo, rotación API keys, detección de riesgo, alerta de emergencia. |
| [`pagos-facturacion.md`](pagos-facturacion.md) | **Pagos y facturación**: flujo completo, Wompi, HMAC, webhook vs frontend. |
| [`despliegue.md`](despliegue.md) | **Despliegue**: Docker, variables de entorno, dev vs prod. |
| [`testing.md`](testing.md) | **Testing**: estructura, ejecución, convenciones. |

---

## Convenciones de esta documentación

- **Todo en español**, tono directo y técnico.
- Rutas de archivo reales (`apps/authentication/models.py`, `static/js/core/shared/alerts.js`, etc.).
- Nombres reales de modelos, campos, endpoints y funciones.
- Diagramas Mermaid donde aporten claridad.
- Al final de cada documento: sección **"Ver también"** con enlaces cruzados.

---

## Cómo contribuir a la documentación

1. Edita el archivo `.md` correspondiente en `docs/`.
2. Usa nombres reales de archivos, clases y funciones tal como aparecen en el código.
3. Actualiza la tabla de contenidos de este `docs/README.md` si añades un nuevo documento.
4. Mantén la sección **"Ver también"** actualizada con enlaces cruzados relevantes.

---

> **Nota:** El archivo `README.md` en la **raíz del repositorio** es la única documentación que queda en la raíz. Cualquier otro `.md` (incluyendo `API.md` y `SEGURIDAD.md`) vive en `docs/`.