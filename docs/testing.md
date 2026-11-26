# Pruebas

Configuración y ejecución de la suite automatizada de PsyAI Connect.

## Configuración

`pytest.ini` define `DJANGO_SETTINGS_MODULE = config.settings.test`, descubre `tests.py` y `test_*.py`, registra el marcador `integration` y usa `--tb=short -q`. No configura `filterwarnings`.

`config/settings/test.py` hereda de `config.settings.dev` y sustituye la conexión por PostgreSQL (por defecto `psyai_connect_test`, localhost:5432). Desactiva las clases y tasas de throttling de DRF y pone `RATELIMIT_ENABLE = False`. No usa SQLite ni un hasher MD5.

## Organización observada

Los archivos de prueba se descubren desde el disco con `find apps tests -name 'test_*.py'`. El árbol relevante es:

```text
apps/
├── admin_panel/tests/ (test_catalogo_roles, test_mantenimiento, test_politicas,
│   test_repositories, test_resumen_dashboard, test_seguridad, test_services, test_views)
├── authentication/tests/ (test_repositories, test_services, test_views)
├── billing/tests/ (test_limpiar_facturas, test_new_flow, test_recordatorios_cobro)
├── chatbot/tests/ (test_repositories, test_services, test_views)
├── core/tests/ (test_arquitectura, test_classes, test_config_pago, test_notificacion_prueba,
│   test_notifier_preferences, test_permissions, test_serve_pages, test_whatsapp)
├── documents/tests/ (test_repositories, test_services, test_views)
├── patients/tests/ (test_anamnesis, test_cita_factura_notificaciones, test_mis_datos,
│   test_notificaciones, test_repositories, test_services, test_views)
├── professionals/tests/ (test_asignaciones, test_consejos, test_deleted_reports_endpoint,
│   test_repositories, test_services, test_views)
└── scheduling/tests/ (test_calificaciones, test_repositories, test_services, test_views)
tests/
```

La suite comprende aproximadamente **835 pruebas en 50 archivos**; el conteo puede variar al cambiar el repositorio.

## Ejecución local

```bash
# Usa PostgreSQL disponible y las variables DB_* adecuadas
$env:DJANGO_SETTINGS_MODULE = "config.settings.test"
pytest

# Solo pruebas no marcadas como integración
pytest -m "not integration"

# Un módulo
pytest apps/chatbot/tests/ -v
```

## Integración continua

El workflow `.github/workflows/ci.yml` se llama **PR checks**. Usa Python 3.13 y el servicio `postgres:16-alpine`; ejecuta `python manage.py check` y `pytest`. No tiene paso de Codecov ni divide la suite en un bloque separado de integración.

## Convenciones

Los tests viven junto a cada app bajo `tests/`; pytest-django prepara Django y la base configurada. El marcador `integration` identifica pruebas que requieren servicios o una base de datos de integración.

## Ver también

- [Despliegue](deployment.md)
- [Arquitectura](architecture.md)
- [Modelos de datos](data-models.md)