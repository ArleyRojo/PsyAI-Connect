import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from apps.core.utils import get_current_user, require_auth, require_role

DoesNotExist = type("DoesNotExist", (Exception,), {})


@pytest.fixture
def rf():
    return RequestFactory()


def _make_request(session_data=None):
    factory = RequestFactory()
    request = factory.get("/api/test")
    if session_data is not None:
        request.session = session_data
    else:
        request.session = {}
    return request


def _make_request_with_mock_session(session_data=None):
    factory = RequestFactory()
    request = factory.get("/api/test")
    mock_session = MagicMock()
    if session_data:
        mock_session.get = lambda key, default=None: session_data.get(key, default)
        mock_session.__contains__ = lambda self, key: key in session_data
    else:
        mock_session.get = lambda key, default=None: default
        mock_session.__contains__ = lambda self, key: False
    request.session = mock_session
    return request


def _mock_db_user(activo=True, estado_cuenta="Activa"):
    user = MagicMock()
    user.activo = activo
    user.estadoCuenta = estado_cuenta
    return user


def _json_response_body(response):
    return json.loads(response.content.decode())


# ── get_current_user tests ────────────────────────────────────────────────


class TestGetCurrentUser:
    def test_returns_none_when_no_session(self):
        request = _make_request()
        assert get_current_user(request) is None

    def test_returns_none_when_no_id_usuario(self):
        request = _make_request({"rol": "paciente", "nombre": "Test"})
        assert get_current_user(request) is None

    def test_returns_user_from_session(self):
        session = {"idUsuario": 1, "rol": "paciente", "nombre": "Test"}
        request = _make_request(session)
        user = get_current_user(request)
        assert user is not None
        assert user["idUsuario"] == 1
        assert user["rol"] == "paciente"
        assert user["nombre"] == "Test"


# ── require_auth tests ───────────────────────────────────────────────────


class TestRequireAuth:
    def test_returns_401_when_no_session(self):
        request = _make_request()
        user, err = require_auth(request)
        assert user is None
        assert err is not None
        assert err.status_code == 401

    def test_returns_401_when_no_id_in_session(self):
        request = _make_request({"rol": "paciente"})
        user, err = require_auth(request)
        assert user is None
        assert err.status_code == 401

    @patch("apps.authentication.models.Register")
    def test_returns_401_when_user_not_in_db(self, MockRegister):
        MockRegister.DoesNotExist = DoesNotExist
        MockRegister.objects.get.side_effect = DoesNotExist()
        request = _make_request_with_mock_session(
            {"idUsuario": 999, "rol": "paciente", "nombre": "Ghost"}
        )
        user, err = require_auth(request)
        assert user is None
        assert err.status_code == 401
        body = _json_response_body(err)
        assert "no encontrado" in body["message"].lower()
        request.session.flush.assert_called_once()

    @patch("apps.authentication.models.Register")
    def test_returns_403_when_user_suspended(self, MockRegister):
        MockRegister.objects.get.return_value = _mock_db_user(
            activo=False, estado_cuenta="Suspendida"
        )
        request = _make_request_with_mock_session(
            {"idUsuario": 1, "rol": "paciente", "nombre": "Test"}
        )
        user, err = require_auth(request)
        assert user is None
        assert err.status_code == 403
        body = _json_response_body(err)
        assert "suspendida" in body["message"].lower()
        request.session.flush.assert_called_once()

    @patch("apps.authentication.models.Register")
    def test_returns_403_when_estado_cuenta_not_activa(self, MockRegister):
        MockRegister.objects.get.return_value = _mock_db_user(
            activo=True, estado_cuenta="Suspendida"
        )
        request = _make_request_with_mock_session(
            {"idUsuario": 1, "rol": "paciente", "nombre": "Test"}
        )
        user, err = require_auth(request)
        assert user is None
        assert err.status_code == 403

    @patch("apps.authentication.models.Register")
    def test_returns_403_when_activo_false_but_estado_activa(self, MockRegister):
        MockRegister.objects.get.return_value = _mock_db_user(
            activo=False, estado_cuenta="Activa"
        )
        request = _make_request_with_mock_session(
            {"idUsuario": 1, "rol": "paciente", "nombre": "Test"}
        )
        user, err = require_auth(request)
        assert user is None
        assert err.status_code == 403

    @patch("apps.authentication.models.Register")
    def test_returns_user_when_active(self, MockRegister):
        MockRegister.objects.get.return_value = _mock_db_user(
            activo=True, estado_cuenta="Activa"
        )
        request = _make_request({"idUsuario": 1, "rol": "paciente", "nombre": "Test"})
        user, err = require_auth(request)
        assert user is not None
        assert user["idUsuario"] == 1
        assert err is None

    @patch("apps.authentication.models.Register")
    def test_session_flushed_on_user_not_found(self, MockRegister):
        MockRegister.DoesNotExist = DoesNotExist
        MockRegister.objects.get.side_effect = DoesNotExist()
        request = _make_request_with_mock_session(
            {"idUsuario": 999, "rol": "paciente", "nombre": "Ghost"}
        )
        require_auth(request)
        request.session.flush.assert_called_once()

    @patch("apps.authentication.models.Register")
    def test_session_flushed_on_suspension(self, MockRegister):
        MockRegister.objects.get.return_value = _mock_db_user(
            activo=False, estado_cuenta="Suspendida"
        )
        request = _make_request_with_mock_session(
            {"idUsuario": 1, "rol": "paciente", "nombre": "Test"}
        )
        require_auth(request)
        request.session.flush.assert_called_once()


# ── require_role tests ───────────────────────────────────────────────────


class TestRequireRole:
    @patch("apps.authentication.models.Register")
    def test_returns_403_when_wrong_role(self, MockRegister):
        MockRegister.objects.get.return_value = _mock_db_user(
            activo=True, estado_cuenta="Activa"
        )
        request = _make_request({"idUsuario": 1, "rol": "paciente", "nombre": "Test"})
        user, err = require_role(request, "admin")
        assert user is None
        assert err.status_code == 403

    @patch("apps.authentication.models.Register")
    def test_returns_user_when_role_matches(self, MockRegister):
        MockRegister.objects.get.return_value = _mock_db_user(
            activo=True, estado_cuenta="Activa"
        )
        request = _make_request({"idUsuario": 1, "rol": "admin", "nombre": "Admin"})
        user, err = require_role(request, "admin")
        assert user is not None
        assert err is None

    @patch("apps.authentication.models.Register")
    def test_returns_403_when_suspended_even_with_correct_role(self, MockRegister):
        MockRegister.objects.get.return_value = _mock_db_user(
            activo=False, estado_cuenta="Suspendida"
        )
        request = _make_request_with_mock_session(
            {"idUsuario": 1, "rol": "admin", "nombre": "Admin"}
        )
        user, err = require_role(request, "admin")
        assert user is None
        assert err.status_code == 403

    def test_returns_401_when_no_session(self):
        request = _make_request()
        user, err = require_role(request, "admin")
        assert user is None
        assert err.status_code == 401
