import json
from unittest.mock import patch, MagicMock

import pytest
from rest_framework.test import APIRequestFactory
from rest_framework import status

from apps.patients.views import (
    PerfilPacienteViewSet,
    EvolucionViewSet,
    PacienteViewSet,
    ProfesionalViewSet,
    ChatbotAPIView,
    ChatbotEncuestaViewSet,
    ChatbotConfigViewSet,
    ConsentimientoChatbotViewSet,
    DocumentoPacienteViewSet,
    ChatContactoViewSet,
    ChatMensajeViewSet,
)
from apps.core.permissions import IsAuthenticatedDRF


@pytest.fixture
def rf():
    return APIRequestFactory()


@pytest.fixture
def mock_service():
    with patch("apps.patients.views._get_patient_service") as m:
        svc = m.return_value
        yield svc


def _auth_paciente(_self, request, view):
    request.user_id = 1
    request.user_role = "paciente"
    request.user_name = "Paciente Test"
    return True


def _auth_profesional(_self, request, view):
    request.user_id = 5
    request.user_role = "profesional"
    request.user_name = "Prof Test"
    return True


def _auth_admin(_self, request, view):
    request.user_id = 10
    request.user_role = "admin"
    request.user_name = "Admin"
    return True


@pytest.fixture
def mock_auth_paciente():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_paciente):
        yield


@pytest.fixture
def mock_role_paciente():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_paciente):
        yield


@pytest.fixture
def mock_role_profesional():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_profesional):
        yield


# ── PerfilPacienteViewSet retrieve ────────────────────────────────────────


class TestPerfilPacienteGet:
    def test_requires_auth(self, rf):
        req = rf.get("/api/patients/perfil/paciente/1")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = PerfilPacienteViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")

        assert resp.status_code == 403

    def test_returns_profile(self, rf, mock_auth_paciente, mock_service):
        req = rf.get("/api/patients/perfil/paciente/1")
        req.session = MagicMock()

        mock_service.get_patient_profile.return_value = (
            {"success": True, "perfil": {"nombre": "Juan"}},
            200,
        )
        view = PerfilPacienteViewSet.as_view({"get": "retrieve"})
        resp = view(req, pk="1")

        assert resp.status_code == 200
        assert resp.data["success"] is True
        mock_service.get_patient_profile.assert_called_once_with(1)

    def test_rejects_other_patient(self, rf, mock_auth_paciente, mock_service):
        req = rf.get("/api/patients/perfil/paciente/99")
        req.session = MagicMock()

        view = PerfilPacienteViewSet.as_view({"get": "retrieve"})
        resp = view(req, pk="99")

        assert resp.status_code == 403

    def test_allows_profesional_to_view(self, rf, mock_service):
        req = rf.get("/api/patients/perfil/paciente/1")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_profesional):
            mock_service.get_patient_profile.return_value = (
                {"success": True, "perfil": {"nombre": "Juan"}},
                200,
            )
            view = PerfilPacienteViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")

        assert resp.status_code == 200

    def test_allows_admin_to_view(self, rf, mock_service):
        req = rf.get("/api/patients/perfil/paciente/1")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_admin):
            mock_service.get_patient_profile.return_value = (
                {"success": True, "perfil": {"nombre": "Juan"}},
                200,
            )
            view = PerfilPacienteViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")

        assert resp.status_code == 200


# ── PerfilPacienteViewSet update ──────────────────────────────────────────


class TestPerfilPacientePut:
    def test_requires_auth(self, rf):
        req = rf.put(
            "/api/patients/perfil/paciente",
            data=json.dumps({"numeroTelefonico": "300123"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = PerfilPacienteViewSet.as_view({"put": "update"})
            resp = view(req)

        assert resp.status_code == 403

    def test_requires_paciente_role(self, rf):
        req = rf.put(
            "/api/patients/perfil/paciente",
            data=json.dumps({"numeroTelefonico": "300123"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_profesional):
            view = PerfilPacienteViewSet.as_view({"put": "update"})
            resp = view(req)

        assert resp.status_code == 403

    def test_updates_profile(self, rf, mock_auth_paciente, mock_service):
        req = rf.put(
            "/api/patients/perfil/paciente",
            data=json.dumps({"numeroTelefonico": "300123"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        mock_service.update_patient_profile.return_value = (
            {"success": True, "message": "Perfil actualizado"},
            200,
        )
        view = PerfilPacienteViewSet.as_view({"put": "update"})
        resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        mock_service.update_patient_profile.assert_called_once()


# ── EvolucionViewSet list ─────────────────────────────────────────────────


class TestEvolucionGet:
    def test_requires_paciente_role(self, rf):
        req = rf.get("/api/patients/evolucion")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = EvolucionViewSet.as_view({"get": "list"})
            resp = view(req)

        assert resp.status_code == 403

    def test_returns_evolution_history(self, rf, mock_role_paciente, mock_service):
        req = rf.get("/api/patients/evolucion")
        req.session = MagicMock()

        mock_service.get_evolution_history.return_value = (
            {"success": True, "historial": []},
            200,
        )
        view = EvolucionViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        mock_service.get_evolution_history.assert_called_once_with(1)


# ── EvolucionViewSet create ───────────────────────────────────────────────


class TestEvolucionPost:
    def test_requires_paciente_role(self, rf):
        req = rf.post(
            "/api/patients/evolucion",
            data=json.dumps({"estadoEmocional": "Ansioso"}),
            content_type="application/json",
        )
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = EvolucionViewSet.as_view({"post": "create"})
            resp = view(req)

        assert resp.status_code == 403

    def test_saves_evolution(self, rf, mock_role_paciente, mock_service):
        req = rf.post(
            "/api/patients/evolucion",
            data=json.dumps({
                "estadoEmocional": "Ansioso",
                "nivelEnergia": 3,
                "notasPersonales": "Me siento bien",
            }),
            content_type="application/json",
        )
        req.session = MagicMock()

        mock_service.save_evolution.return_value = (
            {"success": True, "message": "Evolucion guardada correctamente"},
            200,
        )
        view = EvolucionViewSet.as_view({"post": "create"})
        resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        mock_service.save_evolution.assert_called_once()


# ── PacienteViewSet list ──────────────────────────────────────────────────


class TestPacienteGet:
    def test_requires_profesional_or_admin(self, rf):
        req = rf.get("/api/patients/pacientes")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = PacienteViewSet.as_view({"get": "list"})
            resp = view(req)

        assert resp.status_code == 403

    def test_profesional_can_list(self, rf, mock_role_profesional, mock_service):
        req = rf.get("/api/patients/pacientes")
        req.session = MagicMock()

        mock_service.list_patients.return_value = (
            {"success": True, "pacientes": []},
            200,
        )
        view = PacienteViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        mock_service.list_patients.assert_called_once()

    def test_pagination_params(self, rf, mock_role_profesional, mock_service):
        req = rf.get("/api/patients/pacientes", {"page": "2", "limit": "10"})
        req.session = MagicMock()

        mock_service.list_patients.return_value = (
            {"success": True, "pacientes": []},
            200,
        )
        view = PacienteViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        mock_service.list_patients.assert_called_once_with(2, 10)


# ── ProfesionalViewSet list ───────────────────────────────────────────────


class TestProfesionalGet:
    def test_requires_auth(self, rf):
        req = rf.get("/api/patients/profesionales")
        req.session = MagicMock()

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = ProfesionalViewSet.as_view({"get": "list"})
            resp = view(req)

        assert resp.status_code == 403

    def test_returns_professionals(self, rf, mock_auth_paciente, mock_service):
        req = rf.get("/api/patients/profesionales")
        req.session = MagicMock()

        mock_service.list_professionals.return_value = (
            {"success": True, "profesionales": [{"idUsuario": 5, "nombre": "Dr"}]},
            200,
        )
        view = ProfesionalViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        assert len(resp.data["profesionales"]) == 1
        mock_service.list_professionals.assert_called_once()
