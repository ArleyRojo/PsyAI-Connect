import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from apps.billing.views import (
    FacturaListView,
    FacturaDetailView,
    FacturaPagoView,
    FacturaStatsView,
    ProfesionalPacientesView,
)

BASE_DIR = Path(__file__).resolve().parents[3]

PATCH_TARGET = "apps.core.permissions.IsAuthenticatedDRF.has_permission"
PATCH_GET_USER = "apps.core.permissions.get_current_user"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _user_dict(id_usuario=1, rol="paciente", nombre="Test"):
    return {"idUsuario": id_usuario, "rol": rol, "nombre": nombre}


def _mock_auth_drf(user):
    def side_effect(self, request, view):
        request.user_id = user["idUsuario"]
        request.user_role = user["rol"]
        request.user_name = user.get("nombre", "Test")
        return True

    return side_effect


def _make_request(method="get", path="/facturas/", body=None):
    factory = APIRequestFactory()
    kwargs = {"content_type": "application/json"}
    if method == "get":
        req = factory.get(path, **kwargs)
    elif method == "post":
        req = factory.post(
            path, data=json.dumps(body) if body else b"", **kwargs
        )
    elif method == "patch":
        req = factory.patch(
            path, data=json.dumps(body) if body else b"", **kwargs
        )
    elif method == "delete":
        req = factory.delete(
            path, data=json.dumps(body) if body else b"", **kwargs
        )
    req.session = SessionStore()
    return req


# ── FacturaListView GET ──────────────────────────────────────────────────────


class TestFacturaListViewGet:
    def test_requires_auth(self):
        with patch(PATCH_GET_USER, return_value=None):
            req = _make_request("get")
            resp = FacturaListView.as_view()(req)
            assert resp.status_code == 403

    def test_paciente_calls_list_patient(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_patient_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                req = _make_request("get")
                resp = FacturaListView.as_view()(req)
                mock_svc.list_patient_invoices.assert_called_once_with(1)
                assert resp.status_code == 200

    def test_profesional_calls_list_professional(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(2, "profesional"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_professional_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                req = _make_request("get")
                resp = FacturaListView.as_view()(req)
                mock_svc.list_professional_invoices.assert_called_once()
                assert resp.status_code == 200

    def test_admin_calls_list_all(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(3, "admin"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_all_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                req = _make_request("get")
                resp = FacturaListView.as_view()(req)
                mock_svc.list_all_invoices.assert_called_once()
                assert resp.status_code == 200

    def test_rol_param_no_override_user_rol(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(4, "admin"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_all_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                req = _make_request("get", "/facturas/?rol=paciente")
                resp = FacturaListView.as_view()(req)
                mock_svc.list_all_invoices.assert_called_once()
                assert not mock_svc.list_patient_invoices.called

    def test_rol_desconocido_se_ignora(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(7, "admin"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_all_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                req = _make_request("get", "/facturas/?rol=inventado")
                resp = FacturaListView.as_view()(req)
                mock_svc.list_all_invoices.assert_called_once()
                assert not mock_svc.list_patient_invoices.called
                assert resp.status_code == 200

    def test_user_rol_ausente_devuelve_403(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(8, None))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                req = _make_request("get", "/facturas/")
                resp = FacturaListView.as_view()(req)
                assert resp.status_code == 403
                assert not mock_svc.list_all_invoices.called
                assert not mock_svc.list_patient_invoices.called

    def test_user_rol_ausente_stats_devuelve_403(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(9, None))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                req = _make_request("get", "/facturas/stats")
                resp = FacturaStatsView.as_view()(req)
                assert resp.status_code == 403
                assert not mock_svc.get_admin_stats.called

    def test_profesional_passes_filters(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(5, "profesional"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_professional_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                req = _make_request(
                    "get",
                    "/facturas/?rol=profesional&estado=Pagado&fecha_desde=2025-01-01&fecha_hasta=2025-12-31",
                )
                resp = FacturaListView.as_view()(req)
                mock_svc.list_professional_invoices.assert_called_once_with(
                    5,
                    estado="Pagado",
                    fecha_desde="2025-01-01",
                    fecha_hasta="2025-12-31",
                )
                assert resp.status_code == 200

    def test_admin_passes_filters(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(6, "admin"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_all_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                req = _make_request(
                    "get",
                    "/facturas/?rol=admin&paciente=Juan&profesional=Dra%20Maria&estado=Pendiente&metodoPago=tarjeta&fecha_desde=2025-01-01&fecha_hasta=2025-12-31",
                )
                resp = FacturaListView.as_view()(req)
                mock_svc.list_all_invoices.assert_called_once_with(
                    paciente="Juan",
                    profesional="Dra Maria",
                    estado="Pendiente",
                    metodo_pago="tarjeta",
                    fecha_desde="2025-01-01",
                    fecha_hasta="2025-12-31",
                )
                assert resp.status_code == 200


# ── FacturaListView POST ─────────────────────────────────────────────────────


class TestFacturaListViewPost:
    def test_requires_auth(self):
        with patch(PATCH_GET_USER, return_value=None):
            req = _make_request("post", body={})
            resp = FacturaListView.as_view()(req)
            assert resp.status_code == 403

    def test_paciente_requires_id_profesional(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service"):
                req = _make_request("post", body={"items": []})
                resp = FacturaListView.as_view()(req)
                assert resp.status_code == 400
                assert resp.data["success"] is False
                assert "profesional" in resp.data["message"].lower()

    def test_profesional_requires_id_paciente(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(2, "profesional"))):
            with patch("apps.billing.views.invoice_service"):
                req = _make_request("post", body={"items": []})
                resp = FacturaListView.as_view()(req)
                assert resp.status_code == 400
                assert resp.data["success"] is False
                assert "paciente" in resp.data["message"].lower()

    def test_paciente_delegates_to_service(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(10, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.create_invoice.return_value = (
                    {"success": True, "idFactura": 1},
                    201,
                )
                body = {
                    "idProfesional": 20,
                    "items": [
                        {"descripcion": "Sesion", "precioUnitario": 50000}
                    ],
                }
                req = _make_request("post", body=body)
                resp = FacturaListView.as_view()(req)
                mock_svc.create_invoice.assert_called_once_with(10, 20, body)
                assert resp.status_code == 201

    def test_profesional_delegates_to_service(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(30, "profesional"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.create_invoice.return_value = (
                    {"success": True, "idFactura": 2},
                    201,
                )
                body = {
                    "idPaciente": 40,
                    "items": [
                        {"descripcion": "Consulta", "precioUnitario": 80000}
                    ],
                }
                req = _make_request("post", body=body)
                resp = FacturaListView.as_view()(req)
                mock_svc.create_invoice.assert_called_once_with(40, 30, body)
                assert resp.status_code == 201

    def test_invalid_json_falls_back_to_empty(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "profesional"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.create_invoice.return_value = (
                    {"success": True, "idFactura": 3},
                    201,
                )
                factory = APIRequestFactory()
                req = factory.post(
                    "/facturas/",
                    data=b"not json",
                    content_type="application/json",
                )
                req.session = SessionStore()
                resp = FacturaListView.as_view()(req)
                assert resp.status_code in (200, 201, 400)


# ── FacturaDetailView GET ────────────────────────────────────────────────────


class TestFacturaDetailViewGet:
    def test_requires_auth(self):
        with patch(PATCH_GET_USER, return_value=None):
            req = _make_request("get", "/facturas/1")
            resp = FacturaDetailView.as_view()(req, id_factura=1)
            assert resp.status_code == 403

    def test_delegates_to_service(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_invoice.return_value = (
                    {"success": True, "factura": {}},
                    200,
                )
                req = _make_request("get", "/facturas/42")
                resp = FacturaDetailView.as_view()(req, id_factura=42)
                mock_svc.get_invoice.assert_called_once_with(42, 1, "paciente")
                assert resp.status_code == 200

    def test_not_found(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_invoice.return_value = (
                    {"success": False, "message": "No encontrada"},
                    404,
                )
                req = _make_request("get", "/facturas/999")
                resp = FacturaDetailView.as_view()(req, id_factura=999)
                assert resp.status_code == 404


# ── FacturaDetailView PATCH ──────────────────────────────────────────────────


class TestFacturaDetailViewPatch:
    def test_requires_auth(self):
        with patch(PATCH_GET_USER, return_value=None):
            req = _make_request("patch", "/facturas/1", body={})
            resp = FacturaDetailView.as_view()(req, id_factura=1)
            assert resp.status_code == 403

    def test_annul_with_anular_flag(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.annul_invoice.return_value = ({"success": True}, 200)
                body = {"anular": True, "motivoAnulacion": "No aplica"}
                req = _make_request("patch", "/facturas/10", body=body)
                resp = FacturaDetailView.as_view()(req, id_factura=10)
                mock_svc.annul_invoice.assert_called_once_with(
                    10, "No aplica", 1, "paciente"
                )
                assert resp.status_code == 200

    def test_annul_with_motivo_only(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.annul_invoice.return_value = ({"success": True}, 200)
                body = {"motivoAnulacion": "Cancelado"}
                req = _make_request("patch", "/facturas/11", body=body)
                resp = FacturaDetailView.as_view()(req, id_factura=11)
                mock_svc.annul_invoice.assert_called_once_with(
                    11, "Cancelado", 1, "paciente"
                )


# ── FacturaDetailView DELETE ─────────────────────────────────────────────────


class TestFacturaDetailViewDelete:
    def test_requires_auth(self):
        with patch(PATCH_GET_USER, return_value=None):
            req = _make_request("delete", "/facturas/1")
            resp = FacturaDetailView.as_view()(req, id_factura=1)
            assert resp.status_code == 403

    def test_delete_annuls_invoice(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.annul_invoice.return_value = ({"success": True}, 200)
                body = {"motivoAnulacion": "Solicitado por paciente"}
                req = _make_request("delete", "/facturas/5", body=body)
                resp = FacturaDetailView.as_view()(req, id_factura=5)
                mock_svc.annul_invoice.assert_called_once_with(
                    5, "Solicitado por paciente", 1, "paciente"
                )
                assert resp.status_code == 200

    def test_delete_with_empty_body(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "admin"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.annul_invoice.return_value = ({"success": True}, 200)
                factory = APIRequestFactory()
                req = factory.delete(
                    "/facturas/6", data=b"", content_type="application/json"
                )
                req.session = SessionStore()
                resp = FacturaDetailView.as_view()(req, id_factura=6)
                mock_svc.annul_invoice.assert_called_once_with(
                    6, "", 1, "admin"
                )


# ── FacturaPagoView POST ─────────────────────────────────────────────────────


class TestFacturaPagoViewPost:
    def test_unauthenticated_returns_403(self):
        with patch(PATCH_GET_USER, return_value=None):
            req = _make_request("post", "/facturas/1/pago", body={})
            resp = FacturaPagoView.as_view()(req, id_factura=1)
            assert resp.status_code == 403

    def test_wrong_role_returns_403(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(99, "admin"))):
            req = _make_request("post", "/facturas/1/pago", body={})
            resp = FacturaPagoView.as_view()(req, id_factura=1)
            assert resp.status_code == 403

    def test_profesional_rejected(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "profesional"))):
            req = _make_request("post", "/facturas/1/pago", body={})
            resp = FacturaPagoView.as_view()(req, id_factura=1)
            assert resp.status_code == 403

    def test_delegates_to_init_wompi_payment(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.init_wompi_payment.return_value = (
                    {"success": True, "data": {}},
                    200,
                )
                req = _make_request("post", "/facturas/7/pago", body={})
                resp = FacturaPagoView.as_view()(req, id_factura=7)
                mock_svc.init_wompi_payment.assert_called_once_with(7, 1)
                assert resp.status_code == 200


# ── FacturaPagoView DELETE ───────────────────────────────────────────────────


class TestFacturaPagoViewDelete:
    def test_wrong_role_returns_403(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(99, "profesional"))):
            req = _make_request("delete", "/facturas/1/pago", body={})
            resp = FacturaPagoView.as_view()(req, id_factura=1)
            assert resp.status_code == 403

    def test_delegates_to_cancel_payment(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.cancel_payment.return_value = ({"success": True}, 200)
                req = _make_request("delete", "/facturas/3/pago", body={})
                resp = FacturaPagoView.as_view()(req, id_factura=3)
                mock_svc.cancel_payment.assert_called_once_with(3, 1)
                assert resp.status_code == 200


# ── FacturaPagoView PATCH ────────────────────────────────────────────────────


class TestFacturaPagoViewPatch:
    def test_wrong_role_returns_403(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(99, "admin"))):
            req = _make_request("patch", "/facturas/1/pago", body={})
            resp = FacturaPagoView.as_view()(req, id_factura=1)
            assert resp.status_code == 403

    def test_missing_transaction_id_returns_400(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            req = _make_request("patch", "/facturas/1/pago", body={})
            resp = FacturaPagoView.as_view()(req, id_factura=1)
            assert resp.status_code == 400
            assert (
                "transaccion" in resp.data["message"].lower()
                or "transacción" in resp.data["message"].lower()
            )

    def test_delegates_to_confirm_wompi_payment(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.confirm_wompi_payment.return_value = (
                    {"success": True},
                    200,
                )
                req = _make_request(
                    "patch",
                    "/facturas/8/pago",
                    body={"transactionId": "txn_abc123"},
                )
                resp = FacturaPagoView.as_view()(req, id_factura=8)
                mock_svc.confirm_wompi_payment.assert_called_once_with(
                    8, "txn_abc123", 1
                )
                assert resp.status_code == 200


# ── FacturaStatsView GET ─────────────────────────────────────────────────────


class TestFacturaStatsViewGet:
    def test_requires_auth(self):
        with patch(PATCH_GET_USER, return_value=None):
            req = _make_request("get", "/facturas/stats")
            resp = FacturaStatsView.as_view()(req)
            assert resp.status_code == 403

    def test_admin_calls_get_admin_stats(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "admin"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_admin_stats.return_value = (
                    {"success": True, "stats": {}},
                    200,
                )
                req = _make_request("get", "/facturas/stats?rol=admin")
                resp = FacturaStatsView.as_view()(req)
                mock_svc.get_admin_stats.assert_called_once()
                assert resp.status_code == 200

    def test_paciente_calls_get_patient_stats(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_patient_invoice_stats.return_value = (
                    {"success": True, "stats": {}},
                    200,
                )
                req = _make_request("get", "/facturas/stats?rol=paciente")
                resp = FacturaStatsView.as_view()(req)
                mock_svc.get_patient_invoice_stats.assert_called_once_with(1)
                assert resp.status_code == 200

    def test_profesional_calls_get_professional_patients(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "profesional"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_professional_patients.return_value = (
                    {"success": True, "pacientes": []},
                    200,
                )
                req = _make_request("get", "/facturas/stats?rol=profesional")
                resp = FacturaStatsView.as_view()(req)
                mock_svc.get_professional_patients.assert_called_once_with(1)
                assert resp.status_code == 200

    def test_default_rol_uses_user_rol(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "admin"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_admin_stats.return_value = (
                    {"success": True, "stats": {}},
                    200,
                )
                req = _make_request("get", "/facturas/stats")
                resp = FacturaStatsView.as_view()(req)
                mock_svc.get_admin_stats.assert_called_once()
                assert resp.status_code == 200


# ── ProfesionalPacientesView GET ─────────────────────────────────────────────


class TestProfesionalPacientesViewGet:
    def test_unauthenticated_returns_403(self):
        with patch(PATCH_GET_USER, return_value=None):
            req = _make_request("get", "/facturas/pacientes-profesional")
            resp = ProfesionalPacientesView.as_view()(req)
            assert resp.status_code == 403

    def test_paciente_role_rejected(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            req = _make_request("get", "/facturas/pacientes-profesional")
            resp = ProfesionalPacientesView.as_view()(req)
            assert resp.status_code == 403

    def test_admin_rejected(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "admin"))):
            req = _make_request("get", "/facturas/pacientes-profesional")
            resp = ProfesionalPacientesView.as_view()(req)
            assert resp.status_code == 403

    def test_delegates_to_get_professional_patients(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "profesional"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_professional_patients.return_value = (
                    {
                        "success": True,
                        "pacientes": [
                            {"idUsuario": 1, "nombre": "Paciente"}
                        ],
                    },
                    200,
                )
                req = _make_request(
                    "get", "/facturas/pacientes-profesional"
                )
                resp = ProfesionalPacientesView.as_view()(req)
                mock_svc.get_professional_patients.assert_called_once_with(1)
                assert resp.status_code == 200
                assert resp.data["success"] is True
                assert len(resp.data["pacientes"]) == 1

    def test_empty_patients_list(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "profesional"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_professional_patients.return_value = (
                    {"success": True, "pacientes": []},
                    200,
                )
                req = _make_request(
                    "get", "/facturas/pacientes-profesional"
                )
                resp = ProfesionalPacientesView.as_view()(req)
                assert resp.data["pacientes"] == []


# ── Aislamiento de datos por rol (regresión de seguridad) ───────────────────
#
# El rol se toma siempre de request.user_role, que IsAuthenticatedDRF obtiene
# de la sesión y de la BD. Nunca del query param "rol", que lo controla el
# cliente: con él, cualquier usuario autenticado pedía las facturas y las
# estadísticas globales del sistema.


class TestAislamientoDeDatosPorRol:
    def test_paciente_no_alcanza_todas_las_facturas(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_all_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                resp = FacturaListView.as_view()(
                    _make_request("get", "/facturas/?rol=admin")
                )
                assert not mock_svc.list_all_invoices.called

    def test_paciente_no_escala_con_rol_inventado(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_all_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                resp = FacturaListView.as_view()(
                    _make_request("get", "/facturas/?rol=inventado")
                )
                assert not mock_svc.list_all_invoices.called

    def test_profesional_no_alcanza_facturas_de_otros(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(2, "profesional"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.list_all_invoices.return_value = (
                    {"success": True, "facturas": []},
                    200,
                )
                resp = FacturaListView.as_view()(
                    _make_request("get", "/facturas/?rol=admin")
                )
                assert not mock_svc.list_all_invoices.called

    def test_paciente_no_alcanza_estadisticas_admin(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(1, "paciente"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_admin_stats.return_value = (
                    {"success": True, "stats": {}},
                    200,
                )
                resp = FacturaStatsView.as_view()(
                    _make_request("get", "/facturas/stats?rol=admin")
                )
                assert not mock_svc.get_admin_stats.called

    def test_profesional_no_alcanza_estadisticas_admin(self):
        with patch(PATCH_TARGET, _mock_auth_drf(_user_dict(2, "profesional"))):
            with patch("apps.billing.views.invoice_service") as mock_svc:
                mock_svc.get_admin_stats.return_value = (
                    {"success": True, "stats": {}},
                    200,
                )
                resp = FacturaStatsView.as_view()(
                    _make_request("get", "/facturas/stats?rol=admin")
                )
                assert not mock_svc.get_admin_stats.called


# ── Contrato de rutas front ↔ back ───────────────────────────────────────────


class TestRutasFacturacion:
    """El frontend llama endpoints por URL literal; si divergen de urls.py
    la llamada cae en el catch-all 404 y la vista degrada en silencio."""

    @pytest.mark.parametrize(
        "path,url_name",
        [
            ("/api/facturas", "billing:factura_list"),
            ("/api/facturas/estadisticas-admin", "billing:factura_estadisticas_admin"),
            (
                "/api/facturas/pacientes-profesional",
                "billing:factura_pacientes",
            ),
        ],
    )
    def test_ruta_sin_acentos_es_la_registrada(self, path, url_name):
        assert reverse(url_name) == path

    def test_template_admin_consume_la_url_registrada(self):
        ruta = reverse("billing:factura_estadisticas_admin")
        template = Path(
            BASE_DIR / "templates" / "admin" / "aside-admin" / "facturacion.html"
        ).read_text(encoding="utf-8")
        assert f'fetch("{ruta}"' in template
