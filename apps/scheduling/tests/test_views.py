import json
from unittest.mock import patch, MagicMock

import pytest
from rest_framework import status

from apps.scheduling.views import (
    CitaViewSet,
    CitaDetailViewSet,
    CitaDisponibleResource,
    CitaProximaResource,
    CitaHorarioOcupadoResource,
)
from apps.core.permissions import IsAuthenticatedDRF


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
    request.user_id = 9
    request.user_role = "admin"
    request.user_name = "Admin Test"
    return True


def _auth_other(_self, request, view):
    request.user_id = 1
    request.user_role = "otro"
    request.user_name = "Other"
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


@pytest.fixture
def mock_auth_admin():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_admin):
        yield


@pytest.fixture
def mock_service():
    with patch("apps.scheduling.views.appointment_service") as m:
        yield m


# ── CitaViewSet list ─────────────────────────────────────────────────────


class TestCitaViewSetList:
    def test_requires_auth(self, rf):
        req = rf.get("/api/citas")

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = CitaViewSet.as_view({"get": "list"})
            resp = view(req)

        # Sin autenticación debe devolver 401
        assert resp.status_code == 401

    def test_rejects_unauthorized_role(self, rf):
        req = rf.get("/api/citas")

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_other):
            view = CitaViewSet.as_view({"get": "list"})
            resp = view(req)

        assert resp.status_code == 403

    def test_paciente_role_returns_200(self, rf, mock_auth_paciente, mock_service):
        req = rf.get("/api/citas/paciente")

        mock_service.list_patient_appointments.return_value = (
            {"success": True, "citas": [{"idCita": 1}]}, 200,
        )
        view = CitaViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        mock_service.list_patient_appointments.assert_called_once_with(1)

    def test_profesional_role_returns_200(self, rf, mock_role_profesional, mock_service):
        req = rf.get("/api/citas/profesional")

        mock_service.list_professional_appointments.return_value = (
            {"success": True, "citas": [{"idCita": 1}]}, 200,
        )
        view = CitaViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        mock_service.list_professional_appointments.assert_called_once_with(
            5, page=1, limit=20,
        )

    def test_profesional_with_filter_solicitadas(self, rf, mock_role_profesional, mock_service):
        req = rf.get("/api/citas/profesional", {"filter": "solicitadas"})

        mock_service.list_professional_appointments.return_value = (
            {"success": True, "citas": []}, 200,
        )
        view = CitaViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        mock_service.list_professional_appointments.assert_called_once_with(
            5, pending_only=True,
        )

    def test_profesional_pagination(self, rf, mock_role_profesional, mock_service):
        req = rf.get("/api/citas/profesional", {"page": "2", "limit": "10"})

        mock_service.list_professional_appointments.return_value = (
            {"success": True, "citas": []}, 200,
        )
        view = CitaViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        mock_service.list_professional_appointments.assert_called_once_with(
            5, page=2, limit=10,
        )

    def test_admin_rejected(self, rf, mock_auth_admin, mock_service):
        req = rf.get("/api/citas")

        view = CitaViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 403
        assert not mock_service.list_patient_appointments.called

    def test_paciente_no_alcanza_rama_profesional(self, rf, mock_auth_paciente, mock_service):
        req = rf.get("/api/citas", {"rol": "profesional"})

        mock_service.list_patient_appointments.return_value = (
            {"success": True, "citas": []}, 200,
        )
        view = CitaViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        mock_service.list_patient_appointments.assert_called_once_with(1)
        assert not mock_service.list_professional_appointments.called


# ── CitaViewSet create ───────────────────────────────────────────────────


class TestCitaViewSetCreate:
    def test_requires_role(self, rf):
        req = rf.post(
            "/api/citas",
            data=json.dumps({}),
            content_type="application/json",
        )

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = CitaViewSet.as_view({"post": "create"})
            resp = view(req)

        # Sin autenticación debe devolver 401
        assert resp.status_code == 401

    def test_creates_appointment(self, rf, mock_role_paciente, mock_service):
        req = rf.post(
            "/api/citas",
            data=json.dumps({
                "idProfesional": 5,
                "fecha": "2027-06-15",
                "hora": "10:00",
                "tipoCita": "Presencial",
            }),
            content_type="application/json",
        )

        mock_service.create_appointment.return_value = (
            {"success": True, "idCita": 1}, 200,
        )
        view = CitaViewSet.as_view({"post": "create"})
        resp = view(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        mock_service.create_appointment.assert_called_once()

    def test_profesional_creates_for_authenticated_profesional(
        self, rf, mock_role_profesional, mock_service
    ):
        req = rf.post(
            "/api/citas",
            data=json.dumps({
                "idPaciente": 8,
                "idProfesional": 3,
                "fecha": "2027-06-15",
                "hora": "10:00",
                "tipoCita": "Presencial",
                "motivo": "Seguimiento",
                "creado_por_profesional": True,
            }),
            content_type="application/json",
        )

        mock_service.create_appointment.return_value = (
            {"success": True, "idCita": 1}, 200,
        )
        view = CitaViewSet.as_view({"post": "create"})
        resp = view(req)

        assert resp.status_code == 200
        call_args = mock_service.create_appointment.call_args
        assert call_args.args[1]["idProfesional"] == 5
        assert call_args.kwargs["created_by_professional"] is True

    def test_empty_body_returns_400(self, rf, mock_role_paciente, mock_service):
        req = rf.post(
            "/api/citas",
            data=b"",
            content_type="application/json",
        )

        mock_service.create_appointment.return_value = (
            {"success": False, "message": "Datos incompletos"}, 400,
        )
        view = CitaViewSet.as_view({"post": "create"})
        resp = view(req)

        assert resp.status_code == 400


# ── CitaDetailViewSet partial_update ─────────────────────────────────────


class TestCitaDetailViewSetPartialUpdate:
    def test_requires_profesional_role(self, rf):
        req = rf.patch(
            "/api/citas/1",
            data=json.dumps({"estado": "Completada"}),
            content_type="application/json",
        )

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_paciente):
            view = CitaDetailViewSet.as_view({"patch": "partial_update"})
            resp = view(req, pk=1)

        assert resp.status_code == 403

    def test_updates_status(self, rf, mock_role_profesional, mock_service):
        req = rf.patch(
            "/api/citas/1",
            data=json.dumps({"estado": "Completada"}),
            content_type="application/json",
        )

        mock_service.update_status.return_value = (
            {"success": True, "message": "Cita Completada"}, 200,
        )
        view = CitaDetailViewSet.as_view({"patch": "partial_update"})
        resp = view(req, pk=1)

        assert resp.status_code == 200
        # El servicio ahora recibe extra_data, ajustamos la aserción
        mock_service.update_status.assert_called_once()
        call_args = mock_service.update_status.call_args
        assert call_args.args[0] == 1  # idCita
        assert call_args.args[1] == "Completada"  # estado
        assert call_args.args[2] == 5  # user_id


# ── CitaDetailViewSet destroy ────────────────────────────────────────────


class TestCitaDetailViewSetDestroy:
    def test_requires_role(self, rf):
        req = rf.delete("/api/citas/1")

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_other):
            view = CitaDetailViewSet.as_view({"delete": "destroy"})
            resp = view(req, pk=1)

        assert resp.status_code == 403

    def test_paciente_cancels_appointment(self, rf, mock_role_paciente, mock_service):
        req = rf.delete(
            "/api/citas/1",
            data=json.dumps({"motivoCancelacion": "Cambio de planes"}),
            content_type="application/json",
        )

        mock_service.cancel_appointment.return_value = (
            {"success": True, "message": "Cita cancelada correctamente"}, 200,
        )
        view = CitaDetailViewSet.as_view({"delete": "destroy"})
        resp = view(req, pk=1)

        assert resp.status_code == 200
        mock_service.cancel_appointment.assert_called_once_with(1, 1, "Cambio de planes")

    def test_profesional_cancels_appointment(self, rf, mock_role_profesional, mock_service):
        req = rf.delete(
            "/api/citas/1",
            data=json.dumps({"motivoCancelacion": "Emergencia"}),
            content_type="application/json",
        )

        mock_service.cancel_professional_appointment.return_value = (
            {"success": True, "message": "Cita cancelada correctamente"}, 200,
        )
        view = CitaDetailViewSet.as_view({"delete": "destroy"})
        resp = view(req, pk=1)

        assert resp.status_code == 200
        mock_service.cancel_professional_appointment.assert_called_once_with(1, 5, "Emergencia")

    def test_delete_with_empty_body(self, rf, mock_role_paciente, mock_service):
        req = rf.delete("/api/citas/1")

        mock_service.cancel_appointment.return_value = (
            {"success": False, "message": "Debes indicar el motivo"}, 400,
        )
        view = CitaDetailViewSet.as_view({"delete": "destroy"})
        resp = view(req, pk=1)

        assert resp.status_code == 400
        mock_service.cancel_appointment.assert_called_once_with(1, 1, "")


# ── CitaDisponibleResource GET ───────────────────────────────────────────


class TestCitaDisponibleResourceGet:
    def test_no_auth_required_returns_200(self, rf, mock_service):
        req = rf.get("/api/citas/disponibles", {
            "idProfesional": 5,
            "fecha": "2027-06-15",
        })
        req.path = "/api/citas/disponibles"

        mock_service.get_available_times.return_value = (
            {"success": True, "horarios": ["09:00", "09:30"]}, 200,
        )
        resp = CitaDisponibleResource.as_view()(req)

        assert resp.status_code == 200
        assert "09:00" in resp.data["horarios"]

    def test_fechas_disponibles_path(self, rf, mock_service):
        req = rf.get("/api/citas/fechas-disponibles", {
            "idProfesional": 5,
            "anio": "2027",
            "mes": "6",
        })
        req.path = "/api/citas/fechas-disponibles"

        mock_service.get_available_dates.return_value = (
            {"success": True, "fechas": ["2027-06-15"]}, 200,
        )
        resp = CitaDisponibleResource.as_view()(req)

        assert resp.status_code == 200
        assert "2027-06-15" in resp.data["fechas"]


# ── CitaProximaResource GET ──────────────────────────────────────────────


@pytest.mark.django_db
class TestCitaProximaResourceGet:
    def test_requires_paciente_role(self, rf):
        from apps.authentication.models import Register
        # Crear usuario profesional en la BD de test
        profesional = Register.objects.create_user(
            idUsuario=5, email="prof@test.com", password="pass", rol="profesional", nombre="Prof Test"
        )
        req = rf.get("/api/citas/proxima")
        # Simular sesión de profesional autenticado
        req.session = {}
        req.session["idUsuario"] = profesional.idUsuario

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_profesional):
            resp = CitaProximaResource.as_view()(req)

        # Usuario autenticado pero con rol incorrecto debe devolver 403
        assert resp.status_code == 403

    def test_returns_next_appointment(self, rf, mock_role_paciente, mock_service):
        req = rf.get("/api/citas/proxima")

        mock_service.get_next_patient_appointment.return_value = (
            {"success": True, "cita": {"fecha": "15/06/2027", "hora": "10:00"}}, 200,
        )
        resp = CitaProximaResource.as_view()(req)

        assert resp.status_code == 200
        assert resp.data["success"] is True
        mock_service.get_next_patient_appointment.assert_called_once_with(1)

    def test_returns_null_when_no_appointment(self, rf, mock_role_paciente, mock_service):
        req = rf.get("/api/citas/proxima")

        mock_service.get_next_patient_appointment.return_value = (
            {"success": True, "cita": None}, 200,
        )
        resp = CitaProximaResource.as_view()(req)

        assert resp.status_code == 200
        assert resp.data["cita"] is None
