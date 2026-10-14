import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from apps.authentication.models import Register
from apps.billing.models import Facturas, ItemsFactura


@pytest.mark.django_db
class TestBillingNewFlow:

    def setup_method(self):
        self.client = APIClient()
        # create users
        self.paciente = Register.objects.create_user(email="pac@test.com", password="pass1234", nombre="Paciente Test", rol="paciente")
        self.profesional = Register.objects.create_user(email="pro@test.com", password="pass1234", nombre="Profesional Test", rol="profesional")
        self.admin = Register.objects.create_superuser(email="adm@test.com", password="pass1234", nombre="Admin Test")
        self.client.force_authenticate(user=self.paciente)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_create_invoice_patient(self):
        self.authenticate(self.paciente)
        payload = {
            "idProfesional": self.profesional.idUsuario,
            "items": [{"descripcion": "Consulta", "precioUnitario": "100000"}]
        }
        resp = self.client.post("/api/facturas", payload, format="json")
        assert resp.status_code == 201
        assert resp.json()["success"]
        factura_id = resp.json()["idFactura"]
        factura = Facturas.objects.get(idFactura=factura_id)
        assert factura.estadoPago == "Pendiente"
        assert factura.idPaciente == self.paciente
        assert factura.idProfesional == self.profesional
        assert factura.anulada is False
        assert factura.fechaPago is None

    def test_create_invoice_professional(self):
        self.authenticate(self.profesional)
        payload = {
            "idPaciente": self.paciente.idUsuario,
            "items": [{"descripcion": "Terapia", "precioUnitario": "150000"}]
        }
        resp = self.client.post("/api/facturas", payload, format="json")
        assert resp.status_code == 201
        assert resp.json()["success"]

    def test_list_patient_invoices(self):
        self.authenticate(self.paciente)
        Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("100000"), estadoPago="Pendiente")
        resp = self.client.get("/api/facturas/mias")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]
        assert isinstance(data["facturas"], list)

    def test_professional_filter_by_estado(self):
        self.authenticate(self.profesional)
        Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("100000"), estadoPago="Pendiente")
        Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("200000"), estadoPago="Pagado")
        resp = self.client.get("/api/facturas/emitidas?estado=Pendiente")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]
        for f in data["facturas"]:
            assert f["estadoPago"] == "Pendiente"

    def test_confirmar_pago_by_owner(self):
        self.authenticate(self.profesional)
        factura = Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("100000"), estadoPago="Pendiente")
        resp = self.client.post(f"/api/facturas/{factura.idFactura}/confirmar-pago")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]
        factura.refresh_from_db()
        assert factura.estadoPago == "Pagado"
        assert factura.fechaPago is not None

    def test_confirmar_pago_not_owner_403(self):
        other_prof = Register.objects.create_user(email="other@test.com", password="pass", nombre="Otro", rol="profesional")
        self.authenticate(other_prof)
        factura = Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("100000"), estadoPago="Pendiente")
        resp = self.client.post(f"/api/facturas/{factura.idFactura}/confirmar-pago")
        assert resp.status_code == 403

    def test_confirmar_pago_already_paid_400(self):
        self.authenticate(self.profesional)
        factura = Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("100000"), estadoPago="Pagado")
        resp = self.client.post(f"/api/facturas/{factura.idFactura}/confirmar-pago")
        assert resp.status_code == 400

    def test_annul_invoice_not_paid(self):
        self.authenticate(self.profesional)
        factura = Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("100000"), estadoPago="Pendiente")
        resp = self.client.patch(f"/api/facturas/{factura.idFactura}", {"anular": True, "motivoAnulacion": "Error"})
        assert resp.status_code == 200
        factura.refresh_from_db()
        assert factura.anulada is True
        assert factura.motivoAnulacion == "Error"

    def test_annul_invoice_already_paid_fails(self):
        self.authenticate(self.profesional)
        factura = Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("100000"), estadoPago="Pagado")
        resp = self.client.patch(f"/api/facturas/{factura.idFactura}", {"anular": True, "motivoAnulacion": "Error"})
        assert resp.status_code == 400

    def test_admin_stats(self):
        self.authenticate(self.admin)
        Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("100000"), estadoPago="Pendiente")
        Facturas.objects.create(idPaciente=self.paciente, idProfesional=self.profesional, monto=Decimal("200000"), estadoPago="Pagado")
        resp = self.client.get("/api/facturas/estadisticas-admin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]
        stats = data["stats"]
        assert stats["totalFacturado"] == 300000
        assert stats["totalPagado"] == 200000
        assert stats["totalPendiente"] == 100000
        assert stats["anuladas"] == 0

    def test_unauthenticated_access_denied(self):
        self.client.logout()
        resp = self.client.get("/api/facturas/mias")
        assert resp.status_code in (401, 403)