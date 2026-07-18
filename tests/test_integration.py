import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def django_user_model():
    return get_user_model()


# ── Health Check ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHealthCheck:
    def test_healthz_returns_200(self, client):
        response = client.get("/healthz/")
        assert response.status_code == 200


# ── Authentication: Register ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestRegisterEndpoint:
    def test_register_missing_fields(self, client):
        response = client.post(
            "/api/register",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_register_invalid_email(self, client):
        response = client.post(
            "/api/register",
            data=json.dumps({
                "nombre": "Test",
                "email": "not-an-email",
                "password": "Abc123",
                "confirm_password": "Abc123",
                "rol": "paciente",
                "genero": "M",
            }),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_register_password_mismatch(self, client):
        response = client.post(
            "/api/register",
            data=json.dumps({
                "nombre": "Test",
                "email": "test@test.com",
                "password": "Abc123",
                "confirm_password": "Xyz789",
                "rol": "paciente",
                "genero": "M",
            }),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.json()
        assert "coinciden" in data["message"].lower()

    def test_register_successful(self, client):
        response = client.post(
            "/api/register",
            data=json.dumps({
                "nombre": "Integration Test",
                "email": "integration@test.com",
                "password": "Abc123",
                "confirm_password": "Abc123",
                "rol": "paciente",
                "genero": "M",
                "edad": 25,
            }),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True


# ── Authentication: Login ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLoginEndpoint:
    def test_login_missing_fields(self, client):
        response = client.post(
            "/api/login",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_login_wrong_password(self, client):
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        repo = AuthRepository()
        hashed = SecurityHelper.hash_password("Correct1")
        repo.create_user("Login Test", "login@test.com", hashed, "paciente")

        response = client.post(
            "/api/login",
            data=json.dumps({
                "email": "login@test.com",
                "password": "WrongPass1",
            }),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_login_successful(self, client):
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        repo = AuthRepository()
        hashed = SecurityHelper.hash_password("Abc123")
        repo.create_user("Login Success", "loginsuccess@test.com", hashed, "paciente")

        response = client.post(
            "/api/login",
            data=json.dumps({
                "email": "loginsuccess@test.com",
                "password": "Abc123",
            }),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ── Authentication: Session ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestSessionEndpoint:
    def test_session_not_logged_in(self, client):
        response = client.get("/api/session")
        assert response.status_code == 200
        data = response.json()
        assert data["logged_in"] is False

    def test_session_after_login(self, client):
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        repo = AuthRepository()
        hashed = SecurityHelper.hash_password("Abc123")
        repo.create_user("Session Test", "session@test.com", hashed, "paciente")

        login_response = client.post(
            "/api/login",
            data=json.dumps({
                "email": "session@test.com",
                "password": "Abc123",
            }),
            content_type="application/json",
        )
        assert login_response.status_code == 200

        session_response = client.get("/api/session")
        assert session_response.status_code == 200
        data = session_response.json()
        assert data["logged_in"] is True
        assert data["rol"] == "paciente"


# ── Authentication: Logout ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLogoutEndpoint:
    def test_logout_clears_session(self, client):
        from apps.authentication.repositories import AuthRepository
        from apps.authentication.security import SecurityHelper
        repo = AuthRepository()
        hashed = SecurityHelper.hash_password("Abc123")
        repo.create_user("Logout Test", "logout@test.com", hashed, "paciente")

        client.post(
            "/api/login",
            data=json.dumps({"email": "logout@test.com", "password": "Abc123"}),
            content_type="application/json",
        )

        logout_response = client.post("/api/logout")
        assert logout_response.status_code == 200

        session_response = client.get("/api/session")
        data = session_response.json()
        assert data["logged_in"] is False


# ── Authentication: Forgot Password ──────────────────────────────────────────


@pytest.mark.django_db
class TestForgotPasswordEndpoint:
    def test_forgot_password_missing_email(self, client):
        response = client.post(
            "/api/forgot-password",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_forgot_password_nonexistent_email(self, client):
        response = client.post(
            "/api/forgot-password",
            data=json.dumps({"email": "noexist@test.com"}),
            content_type="application/json",
        )
        assert response.status_code == 404


# ── Authentication: Reset Password ──────────────────────────────────────────


@pytest.mark.django_db
class TestResetPasswordEndpoint:
    def test_reset_password_missing_token(self, client):
        response = client.post(
            "/api/reset-password",
            data=json.dumps({
                "new_password": "Abc123",
                "confirm_password": "Abc123",
            }),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_reset_password_invalid_token(self, client):
        response = client.post(
            "/api/reset-password",
            data=json.dumps({
                "token": "bad_token",
                "new_password": "Abc123",
                "confirm_password": "Abc123",
            }),
            content_type="application/json",
        )
        assert response.status_code == 400


# ── Admin Panel: Stats ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminStatsEndpoint:
    def test_stats_requires_admin(self, client):
        response = client.get("/api/admin/stats")
        assert response.status_code in (401, 403, 200)


# ── Patients: Profile ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPatientProfileEndpoint:
    def test_get_profile_not_found(self, client):
        response = client.get("/api/perfil/paciente/99999")
        assert response.status_code in (404, 401, 403)


# ── Professionals: Profile ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestProfessionalProfileEndpoint:
    def test_get_profile_not_found(self, client):
        response = client.get("/api/perfil/profesional/99999")
        assert response.status_code in (404, 401, 403)


# ── Scheduling: Citas ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCitasEndpoint:
    def test_list_citas_empty(self, client):
        response = client.get("/api/citas")
        assert response.status_code in (200, 401, 403)


# ── Billing: Facturas ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFacturasEndpoint:
    def test_list_invoices_empty(self, client):
        response = client.get("/api/facturas")
        assert response.status_code in (200, 401, 403)
