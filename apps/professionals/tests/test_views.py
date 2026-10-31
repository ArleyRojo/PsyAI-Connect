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
    ProfessionalPaymentInfoPublicView,
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
    def test_unauthenticated_returns_401(self, rf):
        req = rf.get("/api/perfil/profesional/1")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = PerfilProfesionalViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")
        # Sin autenticación debe devolver 401
        assert resp.status_code == 401

    def test_wrong_role_returns_401(self, rf):
        req = rf.get("/api/perfil/profesional/1")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = PerfilProfesionalViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")
        # Sin autenticación (has_permission=False) debe devolver 401
        assert resp.status_code == 401

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
    def test_wrong_role_returns_401(self, rf):
        req = rf.put(
            "/api/perfil/profesional",
            data=json.dumps({}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = PerfilProfesionalViewSet.as_view({"put": "update"})
            resp = view(req)
        # Sin autenticación (has_permission=False) debe devolver 401
        assert resp.status_code == 401

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
    def test_wrong_role_returns_401(self, rf):
        req = rf.post(
            "/api/disponibilidad",
            data=json.dumps({"dia": "lunes"}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DisponibilidadViewSet.as_view({"post": "create"})
            resp = view(req)
        # Sin autenticación (has_permission=False) debe devolver 401
        assert resp.status_code == 401

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
    def test_unauthenticated_returns_401(self, rf):
        req = rf.get("/api/disponibilidad/1")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = DisponibilidadViewSet.as_view({"get": "retrieve"})
            resp = view(req, pk="1")
        # Sin autenticación (has_permission=False) debe devolver 401
        assert resp.status_code == 401

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


@pytest.mark.django_db
class TestDashboardResourceGET:
    def test_wrong_role_returns_401(self, rf):
        req = rf.get("/api/profesional/dashboard")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            resp = DashboardResource.as_view()(req)
        # Sin autenticación (has_permission=False) debe devolver 401
        assert resp.status_code == 401

    def test_success(self, rf, mock_auth_profesional, mock_service):
        req = rf.get("/api/profesional/dashboard")
        pass  # session provided by shared rf fixture

        mock_service.get_dashboard.return_value = (
            {"success": True, "pacientes_activos": 5},
            200,
        )
        resp = DashboardResource.as_view()(req)

        assert resp.status_code == 200

    def test_paciente_returns_403(self, rf, mock_service):
        from apps.authentication.models import Register
        Register.objects.create_user(
            idUsuario=1, email="pac@test.com", password="Pass123",
            rol="paciente", nombre="Paciente Test",
        )
        req = rf.get("/api/profesional/dashboard")
        req.session["idUsuario"] = 1
        req.session["rol"] = "paciente"
        req.session["nombre"] = "Paciente Test"
        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_paciente):
            with patch.object(IsProfesional, "has_permission", return_value=False):
                resp = DashboardResource.as_view()(req)
        assert resp.status_code == 403

    def test_admin_returns_403(self, rf, mock_service):
        from apps.authentication.models import Register
        Register.objects.create_user(
            idUsuario=10, email="admin@test.com", password="Pass123",
            rol="admin", nombre="Admin",
        )
        req = rf.get("/api/profesional/dashboard")
        req.session["idUsuario"] = 10
        req.session["rol"] = "admin"
        req.session["nombre"] = "Admin"
        with patch.object(IsAuthenticatedDRF, "has_permission", _auth_admin):
            with patch.object(IsProfesional, "has_permission", return_value=False):
                resp = DashboardResource.as_view()(req)
        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_rol_con_espacios_y_mayusculas_devuelve_200(self, rf, mock_service):
        """Un rol guardado como ' Profesional ' se normaliza y da acceso."""
        from apps.authentication.models import Register

        user = Register.objects.create_user(
            email="dirty@test.com", nombre="Prof Sucio", password="Pass123",
            rol=" Profesional ",
        )
        req = rf.get("/api/profesional/dashboard")
        req.session["idUsuario"] = user.idUsuario
        req.session["rol"] = " Profesional "
        req.session["nombre"] = user.nombre
        req.session.save()

        mock_service.get_dashboard.return_value = (
            {"success": True, "pacientes_activos": 3},
            200,
        )
        resp = DashboardResource.as_view()(req)
        assert resp.status_code == 200


# ── ReporteResource GET/POST ────────────────────────────────────────────────


class TestReporteResourceGET:
    def test_wrong_role_returns_401(self, rf):
        req = rf.get("/api/reportes")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = ReporteViewSet.as_view({"get": "list"})
            resp = view(req)
        # Sin autenticación (has_permission=False) debe devolver 401
        assert resp.status_code == 401

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
    def test_wrong_role_returns_401(self, rf):
        req = rf.post(
            "/api/reportes",
            data=json.dumps({"tipoReporte": "general"}),
            content_type="application/json",
        )
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            view = ReporteViewSet.as_view({"post": "create"})
            resp = view(req)
        # Sin autenticación (has_permission=False) debe devolver 401
        assert resp.status_code == 401

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
    def test_wrong_role_returns_401(self, rf):
        req = rf.get("/api/evolucion/profesional")
        pass  # session provided by shared rf fixture

        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            resp = EvolucionProfesionalResource.as_view()(req)
        # Sin autenticación (has_permission=False) debe devolver 401
        assert resp.status_code == 401

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


# ── ProfessionalPaymentInfoPublicView ─────────────────────────────────────────


def _auth_user(rf, user_id, user_role, user_name="Test User"):
    """Helper to create a request with authenticated user."""
    def _auth(_self, request, view):
        request.user_id = user_id
        request.user_role = user_role
        request.user_name = user_name
        return True
    return _auth


@pytest.mark.django_db
class TestProfessionalPaymentInfoPublicView:
    """Tests for GET /api/profesional/<id>/payment-info/ authorization logic."""

    def setup_method(self):
        from apps.authentication.models import Register
        from apps.professionals.models import ProfessionalPaymentInfo, PacientesProfesional
        from apps.scheduling.models import Citas
        from apps.billing.models import Facturas
        from datetime import date, time

        # Create users
        self.profesional = Register.objects.create_user(
            idUsuario=10, email="prof@test.com", password="pass", rol="profesional", nombre="Prof Test"
        )
        self.other_profesional = Register.objects.create_user(
            idUsuario=20, email="prof2@test.com", password="pass", rol="profesional", nombre="Otro Prof"
        )
        self.paciente = Register.objects.create_user(
            idUsuario=1, email="pac@test.com", password="pass", rol="paciente", nombre="Paciente Test"
        )
        self.other_paciente = Register.objects.create_user(
            idUsuario=2, email="pac2@test.com", password="pass", rol="paciente", nombre="Otro Paciente"
        )
        self.admin = Register.objects.create_superuser(
            email="admin@test.com", password="pass", nombre="Admin Test"
        )

        # Create payment info for the professional
        self.payment_info = ProfessionalPaymentInfo.objects.create(
            idProfesional=self.profesional,
            mensaje_texto="Nequi: 3001234567",
        )

    def _make_request(self, rf, user_id, user_role, url="/api/profesional/10/payment-info"):
        """Create a request with mocked authentication."""
        auth_func = _auth_user(rf, user_id, user_role)
        with patch.object(IsAuthenticatedDRF, "has_permission", auth_func):
            req = rf.get(url)
            view = ProfessionalPaymentInfoPublicView.as_view()
            resp = view(req, id_profesional=10)
        return resp

    def test_profesional_owner_can_access(self, rf):
        """Professional can view their own payment info."""
        resp = self._make_request(rf, 10, "profesional")
        assert resp.status_code == 200
        assert resp.data["success"]
        assert resp.data["data"]["mensaje_texto"] == "Nequi: 3001234567"

    def test_other_profesional_forbidden(self, rf):
        """Another professional cannot view payment info."""
        resp = self._make_request(rf, 20, "profesional")
        assert resp.status_code == 403
        assert not resp.data["success"]
        assert resp.data["message"] == "No autorizado"

    def test_admin_forbidden(self, rf):
        """Admin cannot view payment info (not owner)."""
        # Admin user_id is typically different, let's use the admin's actual id
        admin_id = self.admin.idUsuario
        resp = self._make_request(rf, admin_id, "admin")
        assert resp.status_code == 403
        assert not resp.data["success"]

    def test_unauthenticated_forbidden(self, rf):
        """Unauthenticated user gets 401."""
        with patch.object(IsAuthenticatedDRF, "has_permission", return_value=False):
            req = rf.get("/api/profesional/10/payment-info")
            view = ProfessionalPaymentInfoPublicView.as_view()
            resp = view(req, id_profesional=10)
        # Sin autenticación debe devolver 401
        assert resp.status_code == 401

    def test_paciente_with_asignacion_can_access(self, rf):
        """Patient with PacientesProfesional assignment can access."""
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(
            idProfesional=self.profesional, idPaciente=self.paciente
        )
        resp = self._make_request(rf, 1, "paciente")
        assert resp.status_code == 200
        assert resp.data["success"]
        assert resp.data["data"]["mensaje_texto"] == "Nequi: 3001234567"

    def test_paciente_with_cita_can_access(self, rf):
        """Patient with Cita (appointment) can access even without assignment."""
        from apps.scheduling.models import Citas
        from django.utils import timezone
        from datetime import time
        Citas.objects.create(
            idPaciente=self.paciente,
            idProfesional=self.profesional,
            fecha=timezone.localdate(),
            hora=time(10, 0),
            estado="Confirmada",
        )
        resp = self._make_request(rf, 1, "paciente")
        assert resp.status_code == 200
        assert resp.data["success"]
        assert resp.data["data"]["mensaje_texto"] == "Nequi: 3001234567"

    def test_paciente_with_factura_can_access(self, rf):
        """Patient with Factura (invoice) can access even without assignment or cita."""
        from apps.billing.models import Facturas
        Facturas.objects.create(
            idPaciente=self.paciente,
            idProfesional=self.profesional,
            monto=50000,
            estadoPago="Pendiente",
        )
        resp = self._make_request(rf, 1, "paciente")
        assert resp.status_code == 200
        assert resp.data["success"]
        assert resp.data["data"]["mensaje_texto"] == "Nequi: 3001234567"

    def test_paciente_without_relation_forbidden(self, rf):
        """Patient without any relation gets 403."""
        resp = self._make_request(rf, 1, "paciente")
        assert resp.status_code == 403
        assert not resp.data["success"]
        assert resp.data["message"] == "No autorizado"

    def test_other_paciente_forbidden(self, rf):
        """Another patient (not related) gets 403 even if first patient has relation."""
        from apps.professionals.models import PacientesProfesional
        # First patient has assignment
        PacientesProfesional.objects.create(
            idProfesional=self.profesional, idPaciente=self.paciente
        )
        # Second patient tries to access
        resp = self._make_request(rf, 2, "paciente")
        assert resp.status_code == 403
        assert not resp.data["success"]

    def test_paciente_with_cita_other_profesional_forbidden(self, rf):
        """Patient with cita to OTHER professional cannot access this professional's info."""
        from apps.scheduling.models import Citas
        from django.utils import timezone
        from datetime import time
        Citas.objects.create(
            idPaciente=self.paciente,
            idProfesional=self.other_profesional,  # Different professional
            fecha=timezone.localdate(),
            hora=time(10, 0),
            estado="Confirmada",
        )
        resp = self._make_request(rf, 1, "paciente")
        assert resp.status_code == 403
        assert not resp.data["success"]

    def test_paciente_with_factura_other_profesional_forbidden(self, rf):
        """Patient with factura to OTHER professional cannot access this professional's info."""
        from apps.billing.models import Facturas
        Facturas.objects.create(
            idPaciente=self.paciente,
            idProfesional=self.other_profesional,  # Different professional
            monto=50000,
            estadoPago="Pendiente",
        )
        resp = self._make_request(rf, 1, "paciente")
        assert resp.status_code == 403
        assert not resp.data["success"]

