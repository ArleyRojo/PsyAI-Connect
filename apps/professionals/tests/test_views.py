import json
from unittest.mock import patch, MagicMock

import pytest
from rest_framework import status

from apps.professionals.views import (
    PerfilProfesionalViewSet,
    DisponibilidadViewSet,
    DashboardResource,
    ReporteViewSet,
    EvolucionProfesionalResource,
    ProfessionalPaymentInfoViewSet,
)
from apps.core.permissions import IsAuthenticatedDRF, IsProfesional


@pytest.fixture
def mock_service():
    with patch("apps.professionals.views._get_prof_service") as m:
        svc = m.return_value
        yield svc


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


def _auth_paciente(_self, request, view):
    request.user_id = 1
    request.user_role = "paciente"
    request.user_name = "Paciente Test"
    return True


@pytest.fixture
def mock_auth_profesional():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_profesional):
        yield


@pytest.fixture
def mock_role_profesional():
    with patch.object(IsAuthenticatedDRF, "has_permission", _auth_profesional):
        yield


# ── PerfilProfesionalResource GET ────────────────────────────────────────────


class TestPerfilProfesionalGET:
    def test_unauthenticated_returns_403(self, rf):
        req = rf.get("/api/perfil/profesional/1")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = PerfilProfesionalViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")
        assert resp.status_code == 403

    def test_wrong_role_returns_403(self, rf):
        req = rf.get("/api/perfil/profesional/1")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = PerfilProfesionalViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")
        assert resp.status_code == 403

    def test_profesional_can_access(self, rf, mock_auth_profesional, mock_service):
        req = rf.get("/api/perfil/profesional/1")
        pass  # session provided by shared rf fixture

        mock_service.get_profile.return_value = (
            {"success": True, "perfil": {"nombre": "Dr. García"}},
            200,
        )
        view = PerfilProfesionalViewSet.as_view({"get": "retrieve"})
        resp = view(req, pk="1")

        assert resp.status_code == 200

    def test_admin_can_access(self, rf, mock_service):
        req = rf.get("/api/perfil/profesional/1")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_admin):
            mock_service.get_profile.return_value = (
                {"success": True, "perfil": {}},
                200,
            )
            view = PerfilProfesionalViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")

        assert resp.status_code == 200

    def test_paciente_can_access(self, rf, mock_service):
        req = rf.get("/api/perfil/profesional/1")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_paciente):
            mock_service.get_profile.return_value = (
                {"success": True, "perfil": {}},
                200,
            )
            view = PerfilProfesionalViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")

        assert resp.status_code == 200


# ── PerfilProfesionalResource PUT ────────────────────────────────────────────


class TestPerfilProfesionalPUT:
    def test_wrong_role_returns_403(self, rf):
        req = rf.put(
            "/api/perfil/profesional",
            data=json.dumps({}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = PerfilProfesionalViewSet.as_view({"put": "update"})
            resp = view(req)
        assert resp.status_code == 403

    def test_ownership_check_rejects_other_user(self, rf, mock_service):
        req = rf.put(
            "/api/perfil/profesional",
            data=json.dumps({"idUsuario": 99, "especialidad": "Psicología"}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_profesional):
            view = PerfilProfesionalViewSet.as_view({"put": "update"})
            resp = view(req)
        assert resp.status_code == 403

    def test_success_update(self, rf, mock_auth_profesional, mock_service):
        req = rf.put(
            "/api/perfil/profesional",
            data=json.dumps({"idUsuario": 5, "especialidad": "Psicología"}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        mock_service.update_profile.return_value = (
            {"success": True, "message": "Perfil actualizado"},
            200,
        )
        view = PerfilProfesionalViewSet.as_view({"put": "update"})
        resp = view(req)

        assert resp.status_code == 200

    def test_user_id_set_automatically(self, rf, mock_auth_profesional, mock_service):
        req = rf.put(
            "/api/perfil/profesional",
            data=json.dumps({"especialidad": "Psicología"}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        mock_service.update_profile.return_value = (
            {"success": True, "message": "Perfil actualizado"},
            200,
        )
        view = PerfilProfesionalViewSet.as_view({"put": "update"})
        resp = view(req)

        assert resp.status_code == 200
        call_data = mock_service.update_profile.call_args[0][0]
        assert call_data["idUsuario"] == 5


# ── DisponibilidadResource POST ──────────────────────────────────────────────


class TestDisponibilidadResourcePOST:
    def test_wrong_role_returns_403(self, rf):
        req = rf.post(
            "/api/disponibilidad",
            data=json.dumps({"dia": "lunes"}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DisponibilidadViewSet.as_view({"post": "create"})
            resp = view(req)
        assert resp.status_code == 403

    def test_success(self, rf, mock_auth_profesional):
        req = rf.post(
            "/api/disponibilidad",
            data=json.dumps({"dia": "lunes", "horaInicio": "09:00"}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        with patch("apps.scheduling.services.DisponibilidadService") as MockSvc:
            mock_svc = MagicMock()
            mock_svc.create_availability.return_value = (
                {"success": True, "message": "Creado"},
                201,
            )
            MockSvc.return_value = mock_svc
            view = DisponibilidadViewSet.as_view({"post": "create"})
            resp = view(req)

        assert resp.status_code == 201


# ── DisponibilidadResource GET ───────────────────────────────────────────────


class TestDisponibilidadResourceGET:
    def test_unauthenticated_returns_403(self, rf):
        req = rf.get("/api/disponibilidad/1")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DisponibilidadViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")
        assert resp.status_code == 403

    def test_profesional_can_access(self, rf, mock_auth_profesional):
        req = rf.get("/api/disponibilidad/1")
        pass  # session provided by shared rf fixture

        with patch("apps.scheduling.services.DisponibilidadService") as MockSvc:
            mock_svc = MagicMock()
            mock_svc.get_availability.return_value = (
                {"success": True, "disponibilidad": []},
                200,
            )
            MockSvc.return_value = mock_svc
            view = DisponibilidadViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")

        assert resp.status_code == 200

    def test_paciente_can_access(self, rf):
        req = rf.get("/api/disponibilidad/1")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_paciente):
            with patch("apps.scheduling.services.DisponibilidadService") as MockSvc:
                mock_svc = MagicMock()
                mock_svc.get_availability.return_value = (
                    {"success": True, "disponibilidad": []},
                    200,
                )
                MockSvc.return_value = mock_svc
                view = DisponibilidadViewSet.as_view({"get": "retrieve"})
                resp = view(req, pk="1")

        assert resp.status_code == 200


# ── DashboardResource GET ────────────────────────────────────────────────────


class TestDashboardResourceGET:
    def test_wrong_role_returns_403(self, rf):
        req = rf.get("/api/profesional/dashboard")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            resp = DashboardResource.as_view()(req)
        assert resp.status_code == 403

    def test_success(self, rf, mock_auth_profesional, mock_service):
        req = rf.get("/api/profesional/dashboard")
        pass  # session provided by shared rf fixture

        mock_service.get_dashboard.return_value = (
            {"success": True, "pacientes_activos": 5},
            200,
        )
        resp = DashboardResource.as_view()(req)

        assert resp.status_code == 200


# ── ReporteResource GET/POST ────────────────────────────────────────────────


class TestReporteResourceGET:
    def test_wrong_role_returns_403(self, rf):
        req = rf.get("/api/reportes")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = ReporteViewSet.as_view({"get": "list"})
            resp = view(req)
        assert resp.status_code == 403

    def test_success(self, rf, mock_auth_profesional, mock_service):
        req = rf.get("/api/reportes")
        pass  # session provided by shared rf fixture

        mock_service.report_overview.return_value = (
            {"success": True, "stats": {}},
            200,
        )
        view = ReporteViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200

    def test_deleted_filter(self, rf, mock_auth_profesional, mock_service):
        req = rf.get("/api/reportes?filter=eliminados")
        pass  # session provided by shared rf fixture

        mock_service.get_deleted_reports.return_value = (
            {"success": True, "reportes": []},
            200,
        )
        view = ReporteViewSet.as_view({"get": "list"})
        resp = view(req)

        assert resp.status_code == 200
        mock_service.get_deleted_reports.assert_called_once_with(5)


class TestReporteResourcePOST:
    def test_wrong_role_returns_403(self, rf):
        req = rf.post(
            "/api/reportes",
            data=json.dumps({"tipoReporte": "general"}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = ReporteViewSet.as_view({"post": "create"})
            resp = view(req)
        assert resp.status_code == 403

    def test_success(self, rf, mock_auth_profesional, mock_service):
        req = rf.post(
            "/api/reportes",
            data=json.dumps({"tipoReporte": "general", "idPaciente": 5}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        mock_service.create_report.return_value = (
            {"success": True, "message": "Reporte generado"},
            200,
        )
        view = ReporteViewSet.as_view({"post": "create"})
        resp = view(req)

        assert resp.status_code == 200


# ── EvolucionProfesionalResource GET ─────────────────────────────────────────


class TestEvolucionProfesionalResourceGET:
    def test_wrong_role_returns_403(self, rf):
        req = rf.get("/api/evolucion/profesional")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            resp = EvolucionProfesionalResource.as_view()(req)
        assert resp.status_code == 403

    def test_success(self, rf, mock_auth_profesional, mock_service):
        req = rf.get("/api/evolucion/profesional")
        pass  # session provided by shared rf fixture

        mock_service.all_evolution.return_value = (
            {"success": True, "historial": []},
            200,
        )
        resp = EvolucionProfesionalResource.as_view()(req)

        assert resp.status_code == 200


# ── ProfessionalPaymentInfoViewSet ──────────────────────────────────────────


@pytest.mark.django_db
class TestProfessionalPaymentInfoViewSet:
    def test_retrieve_and_update(self, rf, mock_auth_profesional):
        from apps.authentication.models import Register
        Register.objects.create_user(idUsuario=5, email="pro5@test.com", password="pass", rol="profesional", nombre="Prof Cinco")

        # GET
        req_get = rf.get("/api/profesional/payment-info")
        view_get = ProfessionalPaymentInfoViewSet.as_view({"get": "retrieve"})
        resp_get = view_get(req_get)
        assert resp_get.status_code == 200
        assert resp_get.data["success"]

        # PUT
        req_put = rf.put(
            "/api/profesional/payment-info",
            data=json.dumps({"mensaje_texto": "Nequi: 3001234567"}),
            content_type="application/json",
        )
        view_put = ProfessionalPaymentInfoViewSet.as_view({"put": "update"})
        resp_put = view_put(req_put)
        assert resp_put.status_code == 200
        assert resp_put.data["success"]

        # verify retrieval reflects updated text
        resp_get2 = view_get(req_get)
        assert resp_get2.data["data"]["mensaje_texto"] == "Nequi: 3001234567"

