import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from apps.authentication.models import Register
from apps.billing.models import Facturas, ItemsFactura
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image


@pytest.mark.django_db
class TestBillingNewFlow:

    def setup_method(self):
        self.client = APIClient()
        self.paciente = Register.objects.create_user(email="pac@test.com", password="pass1234", nombre="Paciente Test", rol="paciente")
        self.profesional = Register.objects.create_user(email="pro@test.com", password="pass1234", nombre="Profesional Test", rol="profesional")
        self.admin = Register.objects.create_superuser(email="adm@test.com", password="pass1234", nombre="Admin Test")
        self.client.force_authenticate(user=self.profesional)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def _create_test_image(self):
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return SimpleUploadedFile("test_evidence.png", img_bytes.read(), content_type="image/png")

    def test_register_payment_success(self):
        self.authenticate(self.profesional)
        # ensure relationship
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(idProfesional=self.profesional, idPaciente=self.paciente)

        evidencia = self._create_test_image()
        items = [{"descripcion": "Consulta", "precioUnitario": "100000"}]
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2026-10-14",
            "metodoPago": "Transferencia",
            "referencia": "REF123",
            "notas": "Prueba",
        }
        # Use multipart
        response = self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")
        assert response.status_code == 201
        data = response.json()
        assert data["success"]
        factura_id = data["idFactura"]
        factura = Facturas.objects.get(idFactura=factura_id)
        assert factura.estadoPago == "Pagado"
        assert factura.metodoPago == "Transferencia"
        assert factura.evidencia
        assert factura.confirmada_por == self.profesional

    def test_register_payment_missing_evidencia(self):
        self.authenticate(self.profesional)
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(idProfesional=self.profesional, idPaciente=self.paciente)

        items = [{"descripcion": "Consulta", "precioUnitario": "100000"}]
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2026-10-14",
            "metodoPago": "Transferencia",
        }
        response = self.client.post("/api/facturas", form_data, format="multipart")
        assert response.status_code == 400
        data = response.json()
        assert not data["success"]
        assert "evidencia" in data["message"].lower() or "adjuntar" in data["message"].lower()

    def test_register_payment_invalid_method(self):
        self.authenticate(self.profesional)
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(idProfesional=self.profesional, idPaciente=self.paciente)

        evidencia = self._create_test_image()
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2026-10-14",
            "metodoPago": "Invalido",
        }
        response = self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")
        assert response.status_code == 400

    def test_register_payment_future_date(self):
        self.authenticate(self.profesional)
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(idProfesional=self.profesional, idPaciente=self.paciente)

        evidencia = self._create_test_image()
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2099-12-31",
            "metodoPago": "Transferencia",
        }
        response = self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")
        assert response.status_code == 400

    def test_register_payment_without_relation(self):
        self.authenticate(self.profesional)
        # no PacientesProfesional link
        evidencia = self._create_test_image()
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2026-10-14",
            "metodoPago": "Transferencia",
        }
        response = self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")
        assert response.status_code == 403

    def test_patient_cannot_create(self):
        self.authenticate(self.paciente)
        evidencia = self._create_test_image()
        form_data = {
            "idProfesional": str(self.profesional.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2026-10-14",
            "metodoPago": "Transferencia",
        }
        response = self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")
        assert response.status_code == 403

    def test_admin_cannot_create(self):
        self.authenticate(self.admin)
        evidencia = self._create_test_image()
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2026-10-14",
            "metodoPago": "Transferencia",
        }
        response = self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")
        assert response.status_code == 403

    def test_evidencia_endpoint(self):
        # create factura with evidencia
        self.authenticate(self.profesional)
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(idProfesional=self.profesional, idPaciente=self.paciente)

        evidencia = self._create_test_image()
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2026-10-14",
            "metodoPago": "Transferencia",
        }
        resp = self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")
        assert resp.status_code == 201
        factura_id = resp.json()["idFactura"]

        # owner professional can view
        self.authenticate(self.profesional)
        resp = self.client.get(f"/api/facturas/{factura_id}/evidencia")
        assert resp.status_code == 200

        # patient can view
        self.authenticate(self.paciente)
        resp = self.client.get(f"/api/facturas/{factura_id}/evidencia")
        assert resp.status_code == 200

        # admin can view
        self.authenticate(self.admin)
        resp = self.client.get(f"/api/facturas/{factura_id}/evidencia")
        assert resp.status_code == 200

        # other professional cannot
        other = Register.objects.create_user(email="other@test.com", password="pass", nombre="Otro", rol="profesional")
        self.authenticate(other)
        resp = self.client.get(f"/api/facturas/{factura_id}/evidencia")
        assert resp.status_code == 403

        # unauthenticated
        self.client.logout()
        resp = self.client.get(f"/api/facturas/{factura_id}/evidencia")
        assert resp.status_code in (401, 403)

    def test_admin_readonly(self):
        self.authenticate(self.admin)
        # list
        resp = self.client.get("/api/facturas")
        assert resp.status_code == 200
        # create attempt
        evidencia = self._create_test_image()
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2026-10-14",
            "metodoPago": "Transferencia",
        }
        resp = self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")
        assert resp.status_code == 403
        # anulable? admin cannot annul
        # create a factura first as profesional
        self.authenticate(self.profesional)
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(idProfesional=self.profesional, idPaciente=self.paciente)
        evidencia = self._create_test_image()
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": '[{"descripcion":"Consulta","precioUnitario":"100000"}]',
            "fechaPago": "2026-10-14",
            "metodoPago": "Transferencia",
        }
        resp = self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")
        factura_id = resp.json()["idFactura"]
        # admin try annul
        self.authenticate(self.admin)
        resp = self.client.patch(f"/api/facturas/{factura_id}", {"motivoAnulacion": "test"})
        assert resp.status_code == 403