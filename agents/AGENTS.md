# PsyAI Connect — guía para agentes de IA

Plataforma web de salud mental: Django 5 + DRF + MySQL, plantillas Django con Bootstrap 5 y JavaScript.
Roles: `paciente`, `profesional`, `admin`. Maneja **datos clínicos sensibles**: ante la duda, gana la opción más segura.

## Equipo de agentes (`agents/`, se invocan con `@nombre`)
| Agente | Responsabilidad |
|---|---|
| `architect` | Mantener la arquitectura Views → Services → Repositories → MySQL y que `docs/` la refleje |
| `django-backend` | Modelos, vistas, servicios, repositorios, API REST y permisos |
| `frontend` | Bootstrap 5, Django Templates, JavaScript y diseño responsive |
| `security-auditor` | Autenticación, autorización, privacidad de datos clínicos, secretos y vulnerabilidades |
| `qa-tester` | pytest + pytest-django, regresiones y validación de flujos |

Flujo habitual: `@architect` plantea el cambio → `@django-backend` y `@frontend` lo implementan → `@qa-tester` lo prueba (pytest completo) → `@security-auditor` y `@architect` lo revisan → `@architect` actualiza `docs/`.

## Comandos
- Pruebas: `pytest` (usa `config.settings.test`, SQLite en memoria). Por app: `pytest apps/scheduling -q`.
- Servidor local: `python manage.py runserver` (`config.settings.dev`).
- Docker (desde la raíz): `docker compose -f docker/docker-compose.yml up`.

## Arquitectura (cada app en `apps/<nombre>/`)
`Views (DRF) → Services → Repositories → MySQL`, más `models.py`, `urls.py`, `serializers.py` y `tests/`.
- Las vistas no tocan el ORM; llaman a servicios. Los servicios no conocen `request`. Solo los repositorios consultan la base.
- El id del usuario sale **siempre de la sesión**, nunca del body ni de la URL (evita IDOR).
- Permisos DRF por rol: `IsPaciente`, `IsProfesional`, `IsAdmin`, `IsAuthenticatedDRF`. Toda vista nueva declara el suyo.
- Escrituras en varias tablas (cita + factura) van en `transaction.atomic()`.

## Frontend
- Django Templates + Bootstrap 5 + JS sin framework. Páginas en `templates/<rol>/aside-<rol>/`; JS en `static/js/modules/<rol>/` y `static/js/core/shared/`.
- Diseño responsive con la grilla y utilidades de Bootstrap; colores desde las variables de `static/css/themes/theme.css` (tema claro/oscuro).
- Notificaciones con `PsyAIAlerts` (nunca `alert()`); `fetch` que modifica datos usa `static/js/core/shared/csrf.js`; modales con `.psyai-modal`.
- Al modificar un script, subir su `?v=` en el HTML que lo carga.

## Reglas de negocio que no se rompen
- Crear una cita **nunca** genera factura. Nace `Pendiente`; solo la profesional la confirma y ahí se crea la factura `Pendiente`.
- El chatbot orienta, **no diagnostica**; la detección de riesgo corre antes que cualquier otra lógica.
- No registrar en logs contenido clínico, mensajes del chat ni evidencias de pago.

## Convenciones
- UI, mensajes y documentación en **español**. Nombres de modelos/campos como ya existen (`idCita`, `estadoPago`).
- No editar migraciones ya aplicadas; crear una nueva. No borrar ni debilitar tests para que pasen.
- Nunca leer, imprimir ni commitear `.env`. Variables nuevas se documentan en `.env.example`.
- `docker/entrypoint.sh` debe mantener finales de línea LF.

## Definición de terminado
`pytest` en verde · tests nuevos por capa afectada · `docs/` actualizado (índice en `docs/README.md`) · revisión de `architect` y `security-auditor` hecha.