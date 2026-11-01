# Documentación Técnica de PsyAI Connect

> **Índice de la carpeta `docs/`** — Aquí vive toda la documentación técnica detallada del proyecto.  
> **Índice de la carpeta `docs/`** — Here lives all the detailed technical documentation of the project.  
> El archivo `README.md` en la **raíz del repositorio** sigue siendo la puerta de entrada general (visión general, instalación rápida, stack tecnológico). Todo lo demás — incluida la referencia completa de la API — se encuentra en esta carpeta.  
> The `README.md` at the **repository root** remains the general entry point (overview, quick install, tech stack). Everything else — including the full API reference — is in this folder.

---

## Tabla de contenidos / Table of contents

| Documento / Document | Descripción / Description |
|-----------|-------------|
| [`api.md`](api.md) | **Referencia completa de endpoints REST** (`/api/...`) por app: autenticación, agenda, facturación, pacientes, profesionales, documentos, chatbot, admin. Incluye método HTTP, autenticación requerida y roles permitidos. | **Complete REST endpoints reference** (`/api/...`) by app: authentication, scheduling, billing, patients, professionals, documents, chatbot, admin. Includes HTTP method, required authentication, and allowed roles. |
| [`security.md`](security.md) | **Estado de seguridad del sistema**: capas preexistentes (autenticación, rate limiting, RBAC, HMAC Wompi, validación de archivos, throttling, CORS, HSTS) y las 6 capas agregadas en la iteración de hardening (CSRF real, rotación de sesión, enlace de recuperación HTTPS, verificación de email, CSP, 2FA/TOTP). | **System security status**: pre-existing layers (authentication, rate limiting, RBAC, Wompi HMAC, file validation, throttling, CORS, HSTS) and the 6 layers added in the hardening iteration (real CSRF, session rotation, HTTPS recovery link, email verification, CSP, 2FA/TOTP). |
| [`data-models.md`](data-models.md) | **Modelo de datos del proyecto**: modelos principales por app (`Register`, `PerfilPaciente`, `PerfilProfesional`, `Citas`, `Facturas`, `Documentos`, `ConversacionesChatbot`, etc.), campos clave, relaciones (FK, M2M) y diagrama entidad-relación en Mermaid. | **Project data model**: main models by app (`Register`, `PerfilPaciente`, `PerfilProfesional`, `Citas`, `Facturas`, `Documentos`, `ConversacionesChatbot`, etc.), key fields, relationships (FK, M2M) and Mermaid entity-relationship diagram. |
| [`roles-and-permissions.md`](roles-and-permissions.md) | **Roles y permisos**: tres roles (`paciente`, `profesional`, `admin`), qué pantallas ve cada uno (`templates/patient/`, `templates/professional/`, `templates/admin/`), clases de permiso DRF (`IsAuthenticatedDRF`, `IsPaciente`, `IsProfesional`, `IsAdmin`, etc.), tabla rol × funcionalidad. | **Roles and permissions**: three roles (`patient`, `professional`, `admin`), what screens each role sees (`templates/patient/`, `templates/professional/`, `templates/admin/`), DRF permission classes (`IsAuthenticatedDRF`, `IsPaciente`, `IsProfesional`, `IsAdmin`, etc.), role × functionality table. |
| [`frontend.md`](frontend.md) | **Organización del frontend**: estructura de `static/js/` (`core/shared/`, `modules/<rol>/`, `base/`), carga de scripts en templates (`templates/base/partials/scripts.html`), sistema de notificaciones `PsyAIAlerts`, tema claro/oscuro (`theme.js`, variables CSS en `theme.css`), convenciones de nombres. | **Frontend organization**: `static/js/` structure (`core/shared/`, `modules/<role>/`, `base/`), script loading in templates (`templates/base/partials/scripts.html`), notification system `PsyAIAlerts`, light/dark theme (`theme.js`, CSS variables in `theme.css`), naming conventions. |
| [`chatbot-ai.md`](chatbot-ai.md) | **Chatbot con Google Gemini**: flujo `enviarMensaje` → `/api/chatbot/enviar` → `services.py`, rotación de API keys, detección de riesgo emocional (alto/medio/bajo) en `services.py`, plantilla de alerta `alerta_riesgo.html`. Aclara que es triaje/apoyo, no sustituto de atención profesional. | **Chatbot with Google Gemini**: flow `enviarMensaje` → `/api/chatbot/enviar` → `services.py`, API key rotation, emotional risk detection (high/medium/low) in `services.py`, alert template `alerta_riesgo.html`. Clarifies it is triage/support, not a substitute for professional care. |
| [`deployment.md`](deployment.md) | **Despliegue con Docker**: `Dockerfile` multi-stage, `docker-compose.yml` (dev) vs `docker-compose.prod.yml` (prod), `entrypoint.sh`, variables de entorno (`.env`, `config/settings/base.py` y `prod.py`), diferencias clave `dev.py` vs `prod.py`. | **Deployment with Docker**: multi-stage `Dockerfile`, `docker-compose.yml` (dev) vs `docker-compose.prod.yml` (prod), `entrypoint.sh`, environment variables (`.env`, `config/settings/base.py` and `prod.py`), key differences `dev.py` vs `prod.py`. |
| [`testing.md`](testing.md) | **Testing**: organización (`pytest.ini`, `conftest.py` raíz, `apps/*/tests/` con `test_repositories.py`, `test_services.py`, `test_views.py`), ejecución (`pytest`, cobertura con `pytest-cov`), convención de capas (repository/service/view) y tests de integración. | **Testing**: organization (`pytest.ini`, root `conftest.py`, `apps/*/tests/` with `test_repositories.py`, `test_services.py`, `test_views.py`), execution (`pytest`, coverage with `pytest-cov`), layer convention (repository/service/view) and integration tests. |
| [`integrations.md`](integrations.md) | **Integraciones externas**: Gemini IA, Twilio WhatsApp, Google OAuth (allauth), correo SMTP, pagos manuales con evidencia y boletín informativo. | **External integrations**: Gemini AI, Twilio WhatsApp, Google OAuth (allauth), SMTP email, manual payments with evidence and newsletter. |

---

## Convenciones de esta documentación / Documentation conventions

- **Todo en español**, tono directo y técnico. / **All in Spanish**, direct and technical tone.
- Rutas de archivo reales (`apps/authentication/models.py`, `static/js/core/shared/alerts.js`, etc.). / Real file paths (`apps/authentication/models.py`, `static/js/core/shared/alerts.js`, etc.).
- Nombres reales de modelos, campos, endpoints y funciones. / Real model, field, endpoint, and function names.
- Diagramas Mermaid donde aporten claridad. / Mermaid diagrams where they add clarity.
- Al final de cada documento: sección **"Ver también"** con enlaces cruzados. / At the end of each document: **"See also"** section with cross-links.

---

## Cómo contribuir a la documentación / How to contribute to documentation

1. Edita el archivo `.md` correspondiente en `docs/`. / Edit the corresponding `.md` file in `docs/`.
2. Usa nombres reales de archivos, clases y funciones tal como aparecen en el código. / Use real file, class, and function names as they appear in the code.
3. Actualiza la tabla de contenidos de este `docs/README.md` si añades un nuevo documento. / Update the table of contents of this `docs/README.md` if you add a new document.
4. Mantén la sección **"Ver también"** actualizada con enlaces cruzados relevantes. / Keep the **"See also"** section updated with relevant cross-links.

---

> **Nota:** El archivo `README.md` en la **raíz del repositorio** es la única documentación que queda en la raíz. Cualquier otro `.md` (incluyendo `API.md` y `SEGURIDAD.md`) vive en `docs/`.  
> **Note:** The `README.md` at the **repository root** is the only documentation remaining at the root. Any other `.md` (including `API.md` and `SECURITY.md`) lives in `docs/`.
