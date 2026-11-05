from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from apps.authentication.models import Register
from apps.billing.models import Facturas, ItemsFactura
from django.core.files.uploadedfile import SimpleUploadedFile
import pytest


@pytest.mark.django_db
class TestBillingNewFlow:

    def setup_method(self):
        self.client = APIClient()
        self.paciente = Register.objects.create_user(email="pac@test.com", password="pass1234", nombre="Paciente Test", rol="paciente")
        self.profesional = Register.objects.create_user(email="pro@test.com", password="pass1234", nombre="Profesional Test", rol="profesional")
        self.other_profesional = Register.objects.create_user(email="pro2@test.com", password="pass1234", nombre="Otro Profesional", rol="profesional")
        self.admin = Register.objects.create_superuser(email="adm@test.com", password="pass1234", nombre="Admin Test")
        self.client.force_authenticate(user=self.profesional)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def _create_test_image(self):
        # 1x1 transparent PNG magic bytes
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return SimpleUploadedFile("test_evidence.png", png_bytes, content_type="image/png")

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

    def test_confirmar_pago_flow(self):
        # 1. Crear factura pendiente (ej: desde cita agendada)
        factura = Facturas.objects.create(
            idPaciente=self.paciente,
            idProfesional=self.profesional,
            monto=Decimal("120000"),
            estadoPago="Pendiente",
        )
        ItemsFactura.objects.create(idFactura=factura, descripcion="Cita Presencial", precioUnitario=Decimal("120000"))

        # Paciente no puede confirmar
        self.authenticate(self.paciente)
        evidencia = self._create_test_image()
        resp = self.client.post(f"/api/facturas/{factura.idFactura}/confirmar-pago", {"evidencia": evidencia}, format="multipart")
        assert resp.status_code == 403

        # Otro profesional no puede confirmar
        self.authenticate(self.other_profesional)
        evidencia = self._create_test_image()
        resp = self.client.post(f"/api/facturas/{factura.idFactura}/confirmar-pago", {"evidencia": evidencia}, format="multipart")
        assert resp.status_code == 403

        # Profesional dueño sin evidencia da 400
        self.authenticate(self.profesional)
        resp = self.client.post(f"/api/facturas/{factura.idFactura}/confirmar-pago", {}, format="multipart")
        assert resp.status_code == 400

        # Profesional dueño con evidencia confirma exitosamente
        evidencia = self._create_test_image()
        resp = self.client.post(
            f"/api/facturas/{factura.idFactura}/confirmar-pago",
            {
                "evidencia": evidencia,
                "metodoPago": "Nequi",
                "referencia": "NQ123",
                "notas": "Pago recibido por Nequi",
            },
            format="multipart",
        )
        assert resp.status_code == 200
        assert resp.json()["success"]

        # Verificar BD
        factura.refresh_from_db()
        assert factura.estadoPago == "Pagado"
        assert factura.metodoPago == "Nequi"
        assert factura.referencia == "NQ123"
        assert factura.confirmada_por == self.profesional
        assert factura.fecha_confirmacion is not None
        assert factura.evidencia

        # Intentar confirmar de nuevo (ya pagada) da 400
        evidencia2 = self._create_test_image()
        resp2 = self.client.post(f"/api/facturas/{factura.idFactura}/confirmar-pago", {"evidencia": evidencia2}, format="multipart")
        assert resp2.status_code == 400


# ── RF-72: Evitar facturas duplicadas ────────────────────────────────────────


class TestDuplicateInvoice:
    def setup_method(self):
        self.client = APIClient()
        self.paciente = Register.objects.create_user(email="pac2@test.com", password="pass1234", nombre="Paciente Dup", rol="paciente")
        self.profesional = Register.objects.create_user(email="pro2@test.com", password="pass1234", nombre="Profesional Dup", rol="profesional")
        self.client.force_authenticate(user=self.profesional)
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(idProfesional=self.profesional, idPaciente=self.paciente)

    def _create_test_image(self):
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return SimpleUploadedFile("test_evidence.png", png_bytes, content_type="image/png")

    def _post_invoice(self, cita_id=None, monto="100000", fecha="2026-10-14"):
        evidencia = self._create_test_image()
        items = [{"descripcion": "Consulta", "precioUnitario": monto}]
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": f'[{{"descripcion":"Consulta","precioUnitario":"{monto}"}}]',
            "fechaPago": fecha,
            "metodoPago": "Transferencia",
            "referencia": "REF",
        }
        if cita_id is not None:
            form_data["idCita"] = str(cita_id)
        return self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")

    def test_duplicada_por_cita_retorna_409(self):
        # Primera factura con cita
        resp1 = self._post_invoice(cita_id=101)
        assert resp1.status_code == 201, f"Primera falló: {resp1.content.decode()}"

        # Segunda factura con misma cita → 409
        resp2 = self._post_invoice(cita_id=101)
        assert resp2.status_code == 409
        data = resp2.json()
        assert data["success"] is False
        assert "duplicada" in data["message"].lower() or "ya existe" in data["message"].lower()

    def test_duplicada_sin_cita_retorna_409(self):
        # Primera factura sin cita
        resp1 = self._post_invoice(cita_id=None)
        assert resp1.status_code == 201, f"Primera falló: {resp1.content.decode()}"

        # Segunda factura sin cita, mismo paciente/profesional/monto/fecha → 409
        resp2 = self._post_invoice(cita_id=None)
        assert resp2.status_code == 409
        data = resp2.json()
        assert data["success"] is False

    def test_factura_anulada_previo_no_bloquea(self):
        # Primera factura sin cita, luego anularla
        resp1 = self._post_invoice(cita_id=None)
        assert resp1.status_code == 201
        factura_id = resp1.json()["idFactura"]

        # Anular la factura
        from apps.billing.models import Facturas
        Facturas.objects.filter(idFactura=factura_id).update(anulada=True)

        # Nueva factura misma cita/profesional/monto/fecha debe funcionar (201)
        resp2 = self._post_invoice(cita_id=None)
        assert resp2.status_code == 201, f"Reintento tras anulación falló: {resp2.content.decode()}"

    def test_factura_distinta_funciona(self):
        # Primera factura
        resp1 = self._post_invoice(cita_id=None, monto="100000")
        assert resp1.status_code == 201

        # Segunda factura con monto diferente → 201
        resp2 = self._post_invoice(cita_id=None, monto="200000")
        assert resp2.status_code == 201, f"Factura distinta falló: {resp2.content.decode()}"


# ── RF-80: Filtro por tipo de servicio en facturas ────────────────────────────


class TestTipoServicioFilter:
    def setup_method(self):
        self.client = APIClient()
        self.paciente = Register.objects.create_user(email="pacts@test.com", password="pass1234", nombre="Paciente TS", rol="paciente")
        self.profesional = Register.objects.create_user(email="prots@test.com", password="pass1234", nombre="Profesional TS", rol="profesional")
        self.client.force_authenticate(user=self.profesional)
        from apps.professionals.models import PacientesProfesional
        PacientesProfesional.objects.create(idProfesional=self.profesional, idPaciente=self.paciente)

    def _create_test_image(self):
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return SimpleUploadedFile("test_evidence.png", png_bytes, content_type="image/png")

    def _post_invoice(self, descripcion="Consulta Psicologica", monto="100000", fecha="2026-10-14", cita_id=None):
        evidencia = self._create_test_image()
        items = [{"descripcion": descripcion, "precioUnitario": monto}]
        form_data = {
            "idPaciente": str(self.paciente.idUsuario),
            "items": f'[{{"descripcion":"{descripcion}","precioUnitario":"{monto}"}}]',
            "fechaPago": fecha,
            "metodoPago": "Transferencia",
            "referencia": "REF",
        }
        if cita_id is not None:
            form_data["idCita"] = str(cita_id)
        return self.client.post("/api/facturas", {**form_data, "evidencia": evidencia}, format="multipart")

    def _get_invoices(self, **params):
        return self.client.get("/api/facturas", params)

    def test_filtro_tipo_servicio_por_descripcion(self):
        self._post_invoice(descripcion="Terapia Cognitivo Conductual", monto="100000")
        self._post_invoice(descripcion="Terapia de Pareja", monto="150000")

        resp = self._get_invoices(tipo_servicio="Cognitivo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        facturas = data["facturas"]
        assert len(facturas) == 1
        assert "Cognitivo" in facturas[0]["items"][0]["descripcion"]

    def test_filtro_tipo_servicio_por_descripcion_con_cita(self):
        # Crear cita (no es necesaria para el filtro, solo contexto)
        from apps.scheduling.models import Citas
        cita = Citas.objects.create(
            idPaciente=self.paciente,
            idProfesional=self.profesional,
            fecha="2026-10-14",
            hora="10:00",
            tipoCita="Primera Consulta",
            estado="Confirmada",
        )

        self._post_invoice(descripcion="Terapia de Primera Consulta", monto="100000", cita_id=cita.idCita)

        resp = self._get_invoices(tipo_servicio="Primera Consulta")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        facturas = data["facturas"]
        assert len(facturas) == 1

    def test_filtro_tipo_servicio_combinado_con_estado(self):
        self._post_invoice(descripcion="Terapia Individual", monto="100000")
        self._post_invoice(descripcion="Terapia de Pareja", monto="150000")

        resp = self._get_invoices(tipo_servicio="Individual", estado="Pagado")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        facturas = data["facturas"]
        assert len(facturas) == 1
        assert "Individual" in facturas[0]["items"][0]["descripcion"]