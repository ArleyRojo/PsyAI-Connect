# Testing — PsyAI Connect

> **Resumen:** Organización de tests, cómo ejecutarlos, convención de capas (repository/service/view) y tests de integración.  
> **Audiencia:** Desarrolladores y QA que escriben o ejecutan tests.

---

## 1. Estructura de tests

```
tests/
├── test_integration.py              # Tests de integración (requieren MySQL)

apps/
├── authentication/
│   └── tests/
│       ├── conftest.py              # Fixtures: mocks de repositorios, servicios
│       ├── test_repositories.py     # Tests de AuthRepository, SecurityRepository
│       ├── test_services.py         # Tests de AuthService
│       └── test_views.py            # Tests de LoginView, RegisterView, etc.
├── billing/
│   └── tests/
│       ├── test_repositories.py
│       ├── test_services.py
│       └── test_views.py
├── chatbot/
│   └── tests/
│       ├── test_repositories.py
│       ├── test_services.py
│       └── test_views.py
├── core/
│   └── tests/
│       ├── test_permissions.py
│       └── test_utils.py
├── documents/
│   └── tests/
├── patients/
│   └── tests/
├── professionals/
│   └── tests/
├── scheduling/
│   └── tests/
└── admin_panel/
    └── tests/
```

---

## 2. Configuración global

### `pytest.ini`
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -q --tb=short
filterwarnings =
    ignore::DeprecationWarning
```

### `config/settings/test.py`
- **BD:** SQLite en memoria (`:memory:`) — tests unitarios rápidos, sin MySQL.
- `DEBUG = False`
- `PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']` — hashing rápido para tests
- `CACHES = LocMemCache`
- `EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'`

### `conftest.py` (raíz)
```python
# Fixtures globales
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass  # Hace que `db` fixture esté disponible en todos los tests
```

---

## 3. Convención de capas

Cada app testa sus 3 capas por separado:

| Capa | Archivo | Qué se testea | Dependencias |
|------|---------|---------------|--------------|
| **Repository** | `test_repositories.py` | Consultas SQL, `create`, `get`, `update`, `delete`, `filter` | `@pytest.mark.django_db` (BD real SQLite) |
| **Service** | `test_services.py` | Lógica de negocio, validaciones, orquestación | Mocks de repositorios (`unittest.mock.patch`) |
| **View** | `test_views.py` | Endpoints HTTP (status, response, permisos) | `RequestFactory` + mock de auth (`get_current_user`) |

> **Regla:** Los tests de **service** NO tocan la BD real; usan mocks. Los tests de **repository** SÍ usan BD (SQLite). Los tests de **view** usan `RequestFactory` + sesión simulada.

---

## 4. Fixtures comunes (`apps/authentication/tests/conftest.py`)

```python
@pytest.fixture
def mock_repo():
    return Mock(spec=AuthRepository)

@pytest.fixture
def mock_security_repo():
    return Mock(spec=SecurityRepository)

@pytest.fixture
def auth_service(mock_repo, mock_security_repo):
    service = AuthService()
    service.repo = mock_repo
    service.security_repo = mock_security_repo
    return service

@pytest.fixture
def user_data():
    return {
        "idUsuario": 1,
        "nombre": "Juan Pérez",
        "email": "juan@test.com",
        "contrasena": "hashed123",
        "rol": "paciente",
        "activo": True,
        "estadoCuenta": "Activa",
    }

@pytest.fixture
def api_client():
    return APIClient()
```

---

## 5. Ejemplos de tests por capa

### 5.1 Repository (`test_repositories.py`)

```python
# apps/authentication/tests/test_repositories.py
import pytest
from apps.authentication.repositories import AuthRepository

@pytest.mark.django_db
class TestAuthRepository:
    def test_create_user(self):
        repo = AuthRepository()
        user_id = repo.create_user(
            nombre="Juan",
            email="juan@test.com",
            password_hash="hashed123",
            rol="paciente",
        )
        assert user_id is not None
        user = Register.objects.get(idUsuario=user_id)
        assert user.email == "juan@test.com"
        assert user.rol == "paciente"

    def test_user_exists_by_email(self):
        repo = AuthRepository()
        Register.objects.create_user("juan@test.com", "Juan", "hashed")
        assert repo.user_exists_by_email("juan@test.com") is True
        assert repo.user_exists_by_email("otro@test.com") is False
```

---

### 5.2 Service (`test_services.py`)

```python
# apps/authentication/tests/test_services.py
import pytest
from apps.authentication.services import AuthService
from apps.authentication.security import SecurityHelper

class TestAuthService:
    def test_register_user_success(self, auth_service, mock_repo):
        mock_repo.user_exists_by_email.return_value = False
        mock_repo.create_user.return_value = 1

        payload, status = auth_service.register_user({
            "nombre": "Juan",
            "email": "juan@test.com",
            "password": "Pass123",
            "confirm_password": "Pass123",
            "rol": "paciente",
            "genero": "Masculino",
        })

        assert status == 201
        assert payload["success"] is True
        mock_repo.create_user.assert_called_once()

    def test_login_user_wrong_password(self, auth_service, mock_repo, user_data):
        mock_repo.get_user_by_email.return_value = user_data
        mock_repo.user_exists_by_email.return_value = True

        # SecurityHelper.verify_password devuelve False
        with patch("apps.authentication.services.SecurityHelper.verify_password", return_value=False):
            payload, status, _ = auth_service.login_user(
                {"email": "juan@test.com", "password": "wrong"}, "127.0.0.1"
            )

        assert status == 401
        assert payload["success"] is False
```

---

### 5.3 View (`test_views.py`)

```python
# apps/authentication/tests/test_views.py
import pytest
from rest_framework.test import RequestFactory
from apps.authentication.views import LoginView
from apps.core.utils import get_current_user

class TestLoginView:
    def test_login_success(self, api_client, user_data):
        with patch("apps.authentication.views.auth_service") as mock_service:
            mock_service.login_user.return_value = (
                {"success": True, "message": "Login exitoso", "usuario": user_data},
                200,
                user_data,
            )

            response = api_client.post(
                "/api/login",
                {"email": "juan@test.com", "password": "Pass123", "rol": "paciente"},
                format="json",
            )

            assert response.status_code == 200
            assert response.data["success"] is True
            assert "usuario" in response.data

    def test_login_requires_csrf(self, api_client):
        # Sin header X-CSRFToken en POST -> 403
        response = api_client.post("/api/login", {"email": "x", "password": "y"}, format="json")
        assert response.status_code == 403
```

---

## 6. Tests de integración (`tests/test_integration.py`)

Requieren MySQL real (no SQLite). Marcados con `@pytest.mark.integration`.

```python
# tests/test_integration.py
import pytest

@pytest.mark.integration
class TestFullAuthFlow:
    def test_register_login_logout(self, api_client):
        # 1. Registro
        resp = api_client.post("/api/register", {
            "nombre": "Test User",
            "email": "integration@test.com",
            "password": "Pass123",
            "confirm_password": "Pass123",
            "rol": "paciente",
            "genero": "Otro",
        }, format="json")
        assert resp.status_code == 201

        # 2. Login
        resp = api_client.post("/api/login", {
            "email": "integration@test.com",
            "password": "Pass123",
            "rol": "paciente",
        }, format="json")
        assert resp.status_code == 200
        assert resp.data["success"] is True

        # 3. Session check
        resp = api_client.get("/api/session")
        assert resp.status_code == 200
        assert resp.data["logged_in"] is True

        # 4. Logout
        resp = api_client.post("/api/logout")
        assert resp.status_code == 200

        # 5. Session expirada
        resp = api_client.get("/api/session")
        assert resp.data["logged_in"] is False
```

**Ejecutar solo integración:**
```bash
pytest tests/test_integration.py -v -m integration
```

---

## 6. Cómo ejecutar tests

### Suite completa (unitarios + SQLite)
```bash
# Configurar settings de test
export DJANGO_SETTINGS_MODULE=config.settings.test

# Todos los tests unitarios
pytest --tb=short -q

# Solo una app
pytest apps/authentication/tests/ -v
pytest apps/billing/tests/ -v
pytest apps/chatbot/tests/ -v

# Solo una capa
pytest apps/authentication/tests/test_services.py -v
pytest apps/authentication/tests/test_repositories.py -v
pytest apps/authentication/tests/test_views.py -v
```

### Con cobertura
```bash
# Terminal
pytest --cov=apps --cov-report=term-missing

# HTML (abrir htmlcov/index.html)
pytest --cov=apps --cov-report=html:htmlcov
```

### Solo tests de integración (requiere MySQL)
```bash
# Levantar MySQL (docker compose up -d db)
docker compose -f docker/docker-compose.yml up -d db

# Ejecutar
pytest tests/test_integration.py -v -m integration
```

### Dentro de Docker
```bash
docker compose -f docker/docker-compose.yml exec app python -m pytest apps/ -q
docker compose -f docker-compose.yml exec app python -m pytest apps/authentication/tests/ -v
```

---

## 7. Cobertura objetivo

| Capa | Cobertura mínima |
|------|------------------|
| Repositories | 90% |
| Services | 85% |
| Views | 80% |
| Global | 80% |

> **Excluir de cobertura:** migraciones, `manage.py`, `settings/*`, `wsgi.py`, `asgi.py`, tests.

```ini
# .coveragerc (opcional)
[run]
omit =
    */migrations/*
    */tests/*
    */manage.py
    */config/settings/*
    */config/wsgi.py
    */config/asgi.py
```

---

## 8. Mocking patterns usados

| Qué mockear | Cómo |
|-------------|------|
| Repositorio en Service | `patch("apps.authentication.services.AuthService.repo", mock_repo)` |
| Servicio externo (Gemini, Wompi, Email) | `patch("apps.chatbot.services.GeminiClient.generate")` |
| `timezone.now()` | `patch("django.utils.timezone.now", return_value=fixed_datetime)` |
| `secrets.token_urlsafe` | `patch("secrets.token_urlsafe", return_value="fixed_token")` |
| `request.session` | `request.session = {"idUsuario": 1, "rol": "paciente"}` |

---

## 8. CI/CD (GitHub Actions ejemplo)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: rootpass
          MYSQL_DATABASE: psyai_connect
        ports: ["3306:3306"]
        options: --health-cmd="mysqladmin ping" --health-interval=10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-django pytest-cov
      - name: Unit tests (SQLite)
        run: |
          export DJANGO_SETTINGS_MODULE=config.settings.test
          pytest --cov=apps --cov-report=xml
      - name: Integration tests (MySQL)
        run: |
          export DJANGO_SETTINGS_MODULE=config.settings.test
          pytest tests/test_integration.py -v -m integration
      - uses: codecov/codecov-action@v3
        with: { files: ./coverage.xml }
```

---

## Ver también

- [`modelos-de-datos.md`](modelos-de-datos.md) — Modelos que se testean
- [`chatbot-ia.md`](chatbot-ia.md) — Tests del servicio de chatbot
- [`pagos-facturacion.md`](pagos-facturacion.md) — Tests del webhook Wompi (HMAC)
- [`seguridad.md`](seguridad.md) — Tests de CSRF, rate limiting, 2FA
- [`despliegue.md`](despliegue.md) — Tests en Docker/CI
- [`frontend.md`](frontend.md) — Tests de utilidades JS (si aplica)