from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest

from apps.billing.services import InvoiceService


# ── InvoiceService.create_invoice ─────────────────────────────────────────────


class TestCreateInvoice:
    def test_missing_items(self, invoice_service):
        payload, status = invoice_service.create_invoice(1, 2, {})
        assert status == 400
        assert payload["success"] is False

    def test_empty_items_list(self, invoice_service):
        payload, status = invoice_service.create_invoice(1, 2, {"items": []})
        assert status == 400

    def test_items_not_a_list(self, invoice_service):
        payload, status = invoice_service.create_invoice(1, 2, {"items": "bad"})
        assert status == 400

    def test_invalid_payment_method(self, invoice_service):
        payload, status = invoice_service.create_invoice(1, 2, {
            "items": [{"descripcion": "Sesión", "precioUnitario": 50000}],
            "metodoPago": "crypto",
        })
        assert status == 400
        assert "método" in payload["message"].lower()

    def test_item_missing_descripcion(self, invoice_service):
        payload, status = invoice_service.create_invoice(1, 2, {
            "items": [{"precioUnitario": 50000}],
            "metodoPago": "tarjeta",
        })
        assert status == 400

    def test_item_missing_precio(self, invoice_service):
        payload, status = invoice_service.create_invoice(1, 2, {
            "items": [{"descripcion": "Sesión"}],
            "metodoPago": "tarjeta",
        })
        assert status == 400

    def test_successful_creation(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.create_invoice.return_value = 42
        payload, status = invoice_service.create_invoice(1, 2, {
            "idCita": 10,
            "items": [{"descripcion": "Sesión", "precioUnitario": 50000}],
            "metodoPago": "tarjeta",
        })
        assert status == 201
        assert payload["success"] is True
        assert payload["idFactura"] == 42
        mock_invoice_repo.create_invoice.assert_called_once()

    def test_repo_exception_returns_500(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.create_invoice.side_effect = Exception("DB error")
        payload, status = invoice_service.create_invoice(1, 2, {
            "items": [{"descripcion": "Sesión", "precioUnitario": 50000}],
            "metodoPago": "tarjeta",
        })
        assert status == 500
        assert payload["success"] is False


# ── InvoiceService.get_invoice ────────────────────────────────────────────────


class TestGetInvoice:
    def test_not_found(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = None
        payload, status = invoice_service.get_invoice(999, 1, "paciente")
        assert status == 404

    def test_forbidden_for_other_patient(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {
            "idPaciente": 1,
            "idProfesional": 2,
            "anulada": False,
        }
        payload, status = invoice_service.get_invoice(1, 99, "paciente")
        assert status == 403

    def test_admin_can_view_any_invoice(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {
            "idPaciente": 1,
            "idProfesional": 2,
            "fecha": datetime(2025, 1, 15, 10, 30),
            "monto": 50000,
            "items": [{"precioUnitario": 50000}],
        }
        payload, status = invoice_service.get_invoice(1, 99, "admin")
        assert status == 200
        assert payload["success"] is True

    def test_formats_dates_and_amounts(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {
            "idPaciente": 1,
            "idProfesional": 1,
            "fecha": datetime(2025, 1, 15, 10, 30),
            "monto": 50000,
            "items": [{"precioUnitario": 50000}],
        }
        payload, status = invoice_service.get_invoice(1, 1, "paciente")
        assert status == 200
        assert isinstance(payload["factura"]["monto"], float)
        assert isinstance(payload["factura"]["items"][0]["precioUnitario"], float)


# ── InvoiceService.update_status ──────────────────────────────────────────────


class TestUpdateStatus:
    def test_invalid_status(self, invoice_service):
        payload, status = invoice_service.update_status(1, "Basura", 1, "admin")
        assert status == 400

    def test_not_found(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_owner.return_value = None
        payload, status = invoice_service.update_status(999, "Pagado", 1, "admin")
        assert status == 404

    def test_cannot_change_annulled(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_owner.return_value = (1, 2, True)
        payload, status = invoice_service.update_status(1, "Pagado", 1, "admin")
        assert status == 400
        assert "anulada" in payload["message"].lower()

    def test_forbidden_for_non_owner(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_owner.return_value = (1, 2, False)
        payload, status = invoice_service.update_status(1, "Pagado", 99, "paciente")
        assert status == 403

    def test_successful_update(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_owner.return_value = (1, 2, False)
        payload, status = invoice_service.update_status(1, "Pagado", 2, "profesional")
        assert status == 200
        assert payload["success"] is True
        mock_invoice_repo.update_payment_status.assert_called_once_with(1, "Pagado")


# ── InvoiceService.annul_invoice ──────────────────────────────────────────────


class TestAnnulInvoice:
    def test_empty_motivo(self, invoice_service):
        payload, status = invoice_service.annul_invoice(1, "", 1, "admin")
        assert status == 400

    def test_whitespace_motivo(self, invoice_service):
        payload, status = invoice_service.annul_invoice(1, "   ", 1, "admin")
        assert status == 400

    def test_not_found(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_owner.return_value = None
        payload, status = invoice_service.annul_invoice(999, "Motivo", 1, "admin")
        assert status == 404

    def test_already_annulled(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_owner.return_value = (1, 2, True)
        payload, status = invoice_service.annul_invoice(1, "Motivo", 1, "admin")
        assert status == 400
        assert "anulada" in payload["message"].lower()

    def test_successful_annul(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_owner.return_value = (1, 2, False)
        payload, status = invoice_service.annul_invoice(1, "Cancelado por paciente", 1, "admin")
        assert status == 200
        mock_invoice_repo.annul_invoice.assert_called_once_with(1, "Cancelado por paciente")


# ── InvoiceService.cancel_payment ─────────────────────────────────────────────


class TestCancelPayment:
    def test_not_found(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = None
        payload, status = invoice_service.cancel_payment(999, 1)
        assert status == 404

    def test_not_own_invoice(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "anulada": False, "estadoPago": "Pendiente"}
        payload, status = invoice_service.cancel_payment(1, 99)
        assert status == 403

    def test_already_annulled(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "anulada": True, "estadoPago": "Pendiente"}
        payload, status = invoice_service.cancel_payment(1, 1)
        assert status == 400

    def test_already_paid(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "anulada": False, "estadoPago": "Pagado"}
        payload, status = invoice_service.cancel_payment(1, 1)
        assert status == 400

    def test_successful_cancel(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "anulada": False, "estadoPago": "Pendiente"}
        payload, status = invoice_service.cancel_payment(1, 1)
        assert status == 200
        mock_invoice_repo.update_payment_status.assert_called_once_with(1, "Cancelado")


# ── InvoiceService.init_wompi_payment ─────────────────────────────────────────


class TestInitWompiPayment:
    def test_not_found(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = None
        payload, status = invoice_service.init_wompi_payment(999, 1)
        assert status == 404

    def test_not_own_invoice(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "anulada": False, "estadoPago": "Pendiente", "monto": 50000}
        payload, status = invoice_service.init_wompi_payment(1, 99)
        assert status == 403

    def test_already_paid(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "anulada": False, "estadoPago": "Pagado", "monto": 50000}
        payload, status = invoice_service.init_wompi_payment(1, 1)
        assert status == 400

    @patch("apps.billing.services.settings")
    def test_missing_wompi_config(self, mock_settings, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "anulada": False, "estadoPago": "Pendiente", "monto": 50000}
        mock_settings.WOMPI_PUBLIC_KEY = None
        mock_settings.WOMPI_INTEGRITY_SECRET = None
        payload, status = invoice_service.init_wompi_payment(1, 1)
        assert status == 500

    @patch("apps.billing.services.settings")
    def test_successful_init(self, mock_settings, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "anulada": False, "estadoPago": "Pendiente", "monto": 50000}
        mock_settings.WOMPI_PUBLIC_KEY = "pub_test_abc"
        mock_settings.WOMPI_INTEGRITY_SECRET = "secret123"
        payload, status = invoice_service.init_wompi_payment(1, 1)
        assert status == 200
        assert payload["success"] is True
        assert payload["data"]["currency"] == "COP"
        assert payload["data"]["amountInCents"] == 5000000
        assert payload["data"]["sandbox"] is True
        mock_invoice_repo.set_payment_reference.assert_called_once()


# ── InvoiceService.list_patient_invoices ──────────────────────────────────────


class TestListPatientInvoices:
    def test_returns_formatted_list(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.list_invoices_by_patient.return_value = [
            {"fecha": datetime(2025, 1, 15), "monto": 50000, "items": [{"precioUnitario": 50000}]},
        ]
        payload, status = invoice_service.list_patient_invoices(1)
        assert status == 200
        assert len(payload["facturas"]) == 1
        assert isinstance(payload["facturas"][0]["monto"], float)


# ── InvoiceService.confirm_wompi_payment ──────────────────────────────────────


class TestConfirmWompiPayment:
    def test_not_found(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = None
        payload, status = invoice_service.confirm_wompi_payment(999, "txn_123", 1)
        assert status == 404

    def test_not_own_invoice(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "estadoPago": "Pendiente", "referenciaPago": "ref"}
        payload, status = invoice_service.confirm_wompi_payment(1, "txn_123", 99)
        assert status == 403

    def test_already_paid(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_by_id.return_value = {"idPaciente": 1, "estadoPago": "Pagado", "referenciaPago": "ref"}
        payload, status = invoice_service.confirm_wompi_payment(1, "txn_123", 1)
        assert status == 200
        assert "pagada" in payload["message"].lower()


# ── InvoiceService.get_patient_invoice_stats ──────────────────────────────────


class TestGetPatientInvoiceStats:
    def test_returns_stats(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_stats_by_patient.return_value = {
            "totalPagado": 100000,
            "totalPendiente": 50000,
            "totalGeneral": 150000,
        }
        payload, status = invoice_service.get_patient_invoice_stats(1)
        assert status == 200
        assert payload["stats"]["totalPagado"] == 100000
        mock_invoice_repo.get_invoice_stats_by_patient.assert_called_once_with(1)
        assert not mock_invoice_repo.get_invoice_stats_by_professional.called


# ── InvoiceService.get_admin_stats ────────────────────────────────────────────


class TestGetAdminStats:
    def test_returns_stats(self, invoice_service, mock_invoice_repo):
        mock_invoice_repo.get_invoice_stats_all.return_value = {
            "totalFacturado": 500000,
            "totalPagado": 300000,
            "totalPendiente": 200000,
            "anuladas": 3,
        }
        payload, status = invoice_service.get_admin_stats()
        assert status == 200
        assert payload["stats"]["anuladas"] == 3
