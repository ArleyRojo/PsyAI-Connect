import json
from unittest.mock import patch, MagicMock

import pytest

from apps.authentication.views import (
    RegisterView,
    LoginView,
    LogoutView,
    SessionView,
    ForgotPasswordView,
    ResetPasswordView,
)


# ── RegisterView ─────────────────────────────────────────────────────────────


class TestRegisterView:
    def test_register_success(self, rf):
        req = rf.post(
            "/api/auth/register",
            data=json.dumps({
                "nombre": "Test User",
                "email": "test@test.com",
                "password": "Abc123",
                "confirm_password": "Abc123",
                "rol": "paciente",
                "genero": "M",
            }),
            content_type="application/json",
        )

        with patch("apps.authentication.views.auth_service") as mock_svc:
            mock_svc.register_user.return_value = (
                {"success": True, "message": "Registro exitoso"},
                201,
            )
            resp = RegisterView.as_view()(req)

        resp.render()
        assert resp.status_code == 201
        data = json.loads(resp.content)
        assert data["success"] is True
        mock_svc.register_user.assert_called_once()

    def test_register_validation_error(self, rf):
        req = rf.post(
            "/api/auth/register",
            data=json.dumps({"email": "bad"}),
            content_type="application/json",
        )

        resp = RegisterView.as_view()(req)

        resp.render()
        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert isinstance(data, dict)


# ── LoginView ────────────────────────────────────────────────────────────────


class TestLoginView:
    def test_login_success(self, rf):
        req = rf.post(
            "/api/auth/login",
            data=json.dumps({"email": "test@test.com", "password": "Abc123"}),
            content_type="application/json",
        )
        mock_session = MagicMock()
        mock_session.get.return_value = None
        req.session = mock_session

        session_user = {
            "id": 1,
            "nombre": "Test User",
            "email": "test@test.com",
            "rol": "paciente",
            "fotoPerfil": None,
        }

        with patch("apps.authentication.views.auth_service") as mock_svc:
            mock_svc.login_user.return_value = (
                {"success": True, "message": "Login exitoso"},
                200,
                session_user,
            )
            mock_svc.is_totp_enabled.return_value = False
            with patch("apps.authentication.views.Register") as mock_reg:
                mock_user = MagicMock()
                mock_user.idUsuario = 1
                mock_reg.objects.get.return_value = mock_user
                with patch("apps.authentication.views.django_login"):
                    resp = LoginView.as_view()(req)

        resp.render()
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["success"] is True
        req.session.__setitem__.assert_any_call("usuario", session_user)
        req.session.__setitem__.assert_any_call("idUsuario", 1)
        req.session.__setitem__.assert_any_call("nombre", "Test User")
        req.session.__setitem__.assert_any_call("rol", "paciente")

    def test_login_wrong_password(self, rf):
        req = rf.post(
            "/api/auth/login",
            data=json.dumps({"email": "test@test.com", "password": "Wrong1"}),
            content_type="application/json",
        )
        mock_session = MagicMock()
        mock_session.get.return_value = None
        req.session = mock_session

        with patch("apps.authentication.views.auth_service") as mock_svc:
            mock_svc.login_user.return_value = (
                {"success": False, "message": "Credenciales incorrectas"},
                401,
                None,
            )
            resp = LoginView.as_view()(req)

        resp.render()
        assert resp.status_code == 401
        data = json.loads(resp.content)
        assert data["success"] is False

    def test_login_sets_session_keys(self, rf):
        req = rf.post(
            "/api/auth/login",
            data=json.dumps({"email": "test@test.com", "password": "Abc123"}),
            content_type="application/json",
        )
        mock_session = MagicMock()
        mock_session.get.return_value = None
        req.session = mock_session

        session_user = {
            "id": 5,
            "nombre": "Jane",
            "email": "jane@test.com",
            "rol": "profesional",
            "fotoPerfil": "photos/jane.jpg",
        }

        with patch("apps.authentication.views.auth_service") as mock_svc:
            mock_svc.login_user.return_value = (
                {"success": True, "message": "Login exitoso"},
                200,
                session_user,
            )
            mock_svc.is_totp_enabled.return_value = False
            with patch("apps.authentication.views.Register") as mock_reg:
                mock_user = MagicMock()
                mock_user.idUsuario = 5
                mock_reg.objects.get.return_value = mock_user
                with patch("apps.authentication.views.django_login"):
                    resp = LoginView.as_view()(req)

        resp.render()
        assert resp.status_code == 200
        calls = {c[0][0]: c[0][1] for c in req.session.__setitem__.call_args_list}
        assert calls["usuario"] == session_user
        assert calls["idUsuario"] == 5
        assert calls["nombre"] == "Jane"
        assert calls["rol"] == "profesional"
        assert calls["fotoPerfil"] == "photos/jane.jpg"


# ── LogoutView ───────────────────────────────────────────────────────────────


class TestLogoutView:
    def test_logout_returns_200(self, rf):
        req = rf.post("/api/auth/logout")
        mock_session = MagicMock()
        mock_session.get.return_value = None
        req.session = mock_session

        resp = LogoutView.as_view()(req)

        resp.render()
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["success"] is True
        assert "cerrada" in data["message"].lower()
        req.session.flush.assert_called_once()


# ── SessionView ──────────────────────────────────────────────────────────────


class TestSessionView:
    @pytest.mark.django_db
    def test_logged_in_returns_user_data(self, rf):
        req = rf.get("/api/auth/session")
        req.session = {
            "idUsuario": 1,
            "nombre": "Test User",
            "rol": "paciente",
            "fotoPerfil": None,
        }

        resp = SessionView.as_view()(req)

        resp.render()
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["logged_in"] is True
        assert data["usuario"]["idUsuario"] == 1
        assert data["usuario"]["nombre"] == "Test User"
        assert data["usuario"]["rol"] == "paciente"

    def test_not_logged_in(self, rf):
        req = rf.get("/api/auth/session")
        req.session = {}

        resp = SessionView.as_view()(req)

        resp.render()
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["logged_in"] is False


# ── ForgotPasswordView ──────────────────────────────────────────────────────


class TestForgotPasswordView:
    def test_forgot_password_success(self, rf):
        req = rf.post(
            "/api/auth/forgot-password",
            data=json.dumps({"email": "user@test.com"}),
            content_type="application/json",
        )
        req.META["SERVER_NAME"] = "localhost"
        req.META["SERVER_PORT"] = "8000"

        with patch("apps.authentication.views.auth_service") as mock_svc:
            mock_svc.recover_password.return_value = (
                {"success": True, "message": "Fue enviado al correo."},
                200,
            )
            resp = ForgotPasswordView.as_view()(req)

        resp.render()
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["success"] is True
        mock_svc.recover_password.assert_called_once()


# ── ResetPasswordView ───────────────────────────────────────────────────────


class TestResetPasswordView:
    def test_reset_password_success(self, rf):
        req = rf.post(
            "/api/auth/reset-password",
            data=json.dumps({
                "token": "valid_token",
                "new_password": "NewPass1",
                "confirm_password": "NewPass1",
            }),
            content_type="application/json",
        )

        with patch("apps.authentication.views.auth_service") as mock_svc:
            mock_svc.reset_password.return_value = (
                {"success": True, "message": "Contraseña actualizada exitosamente"},
                200,
            )
            resp = ResetPasswordView.as_view()(req)

        resp.render()
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["success"] is True
        mock_svc.reset_password.assert_called_once()
