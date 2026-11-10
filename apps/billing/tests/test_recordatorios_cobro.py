"""Pruebas de los recordatorios de cobro (HU-77)."""
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.authentication.models import Register
from apps.authentication.security import SecurityHelper
from apps.billing import recordatorios
from apps.billing.models import Facturas, ItemsFactura
from apps.scheduling.models import Citas, Notificaciones


def _usuario(email, rol, nombre):
    return Register.objects.create(
        nombre=nombre, email=email, contrasena=SecurityHelper.hash_password("Clave123*"),
        rol=rol, activo=True, estadoCuenta="Activa",
    )


@pytest.fixture
def paciente():
    return _usuario("pac@test.com", "paciente", "Juan Pérez")


@pytest.fixture
def profesional():
    return _usuario("pro@test.com", "profesional", "Dra. Ruiz")


def _factura(paciente, profesional, dias=4, monto="100000", **extra):
    f = Facturas.objects.create(idPaciente=paciente, idProfesional=profesional, monto=Decimal(monto), **extra)
    ItemsFactura.objects.create(idFactura=f, descripcion="Consulta", precioUnitario=Decimal(monto))
    Facturas.objects.filter(pk=f.pk).update(fecha=timezone.now() - timedelta(days=dias))
    f.refresh_from_db()
    return f


def _avisos(paciente):
    return Notificaciones.objects.filter(idUsuario=paciente, canal="interno", tipo="Factura")


@pytest.mark.django_db
class TestAutomaticos:
    def test_primer_aviso_a_los_3_dias(self, paciente, profesional):
        _factura(paciente, profesional, dias=2)

        assert recordatorios.enviar_automaticos() == (0, 0)

        vieja = _factura(paciente, profesional, dias=4)
        assert recordatorios.enviar_automaticos() == (1, 1)
        vieja.refresh_from_db()
        assert vieja.recordatoriosEnviados == 1
        assert vieja.ultimoRecordatorio is not None

    def test_luego_cada_7_dias_y_maximo_4(self, paciente, profesional):
        factura = _factura(paciente, profesional, dias=60)
        ahora = timezone.now()

        assert recordatorios.enviar_automaticos(ahora) == (1, 1)
        assert recordatorios.enviar_automaticos(ahora + timedelta(days=6)) == (0, 0)
        for semana in range(1, 4):
            assert recordatorios.enviar_automaticos(ahora + timedelta(days=7 * semana)) == (1, 1)
        assert recordatorios.enviar_automaticos(ahora + timedelta(days=28)) == (0, 0)

        factura.refresh_from_db()
        assert factura.recordatoriosEnviados == 4

    def test_no_recuerda_pagadas_ni_anuladas(self, paciente, profesional):
        _factura(paciente, profesional, estadoPago="Pagado")
        _factura(paciente, profesional, anulada=True, motivoAnulacion="Error")

        assert recordatorios.enviar_automaticos() == (0, 0)

    def test_un_solo_aviso_por_paciente_con_el_detalle(self, paciente, profesional):
        _factura(paciente, profesional, monto="100000")
        _factura(paciente, profesional, monto="50000")

        assert recordatorios.enviar_automaticos() == (1, 2)

        aviso = _avisos(paciente).get()
        assert "2 facturas pendientes por un total de $150.000" in aviso.mensaje
        assert "Dra. Ruiz" in aviso.mensaje

    def test_respeta_la_preferencia_de_facturas(self, paciente, profesional):
        _factura(paciente, profesional)

        with patch("apps.core.notifier.notificar_paciente", return_value=False) as notificar:
            recordatorios.enviar_automaticos()

        assert notificar.call_args.args[3] == "factura"  # el notificador filtra por "recibirFacturas"
        assert _avisos(paciente).count() == 1  # la campanita siempre

    def test_comando(self, paciente, profesional):
        _factura(paciente, profesional)

        call_command("enviar_recordatorios_cobro")

        assert _avisos(paciente).count() == 1


@pytest.mark.django_db
class TestManual:
    def test_el_profesional_recuerda_su_factura(self, paciente, profesional):
        factura = _factura(paciente, profesional, dias=0)

        payload, status = recordatorios.recordar_manual(factura.idFactura, profesional.idUsuario)

        assert status == 200
        assert payload["recordatoriosEnviados"] == 1
        assert _avisos(paciente).count() == 1

    def test_maximo_uno_cada_24_horas(self, paciente, profesional):
        factura = _factura(paciente, profesional)
        recordatorios.recordar_manual(factura.idFactura, profesional.idUsuario)

        _, status = recordatorios.recordar_manual(factura.idFactura, profesional.idUsuario)

        assert status == 429

    def test_no_puede_recordar_factura_ajena_ni_pagada(self, paciente, profesional):
        otro = _usuario("otro@test.com", "profesional", "Otro")
        factura = _factura(paciente, profesional)
        pagada = _factura(paciente, profesional, estadoPago="Pagado")

        assert recordatorios.recordar_manual(factura.idFactura, otro.idUsuario)[1] == 403
        assert recordatorios.recordar_manual(pagada.idFactura, profesional.idUsuario)[1] == 400

    def test_por_la_api(self, client, paciente, profesional):
        factura = _factura(paciente, profesional)

        client.post("/api/login", data=json.dumps({"email": "pro@test.com", "password": "Clave123*", "rol": "profesional"}),
                    content_type="application/json")
        r = client.post(f"/api/facturas/{factura.idFactura}/recordar")

        assert r.status_code == 200
        assert "Juan Pérez" in r.json()["message"]


@pytest.mark.django_db
def test_recordatorio_de_cita_usa_la_hora_de_colombia(paciente, profesional):
    """La cita se guarda en hora local; antes el comando comparaba con la hora UTC."""
    manana = timezone.localtime() + timedelta(hours=24)
    cita = Citas.objects.create(
        idPaciente=paciente, idProfesional=profesional, fecha=manana.date(),
        hora=time(manana.hour, manana.minute), tipoCita="Virtual", motivo="Control", estado="Confirmada",
    )

    with patch("apps.scheduling.management.commands.enviar_recordatorios.notificar_paciente", return_value=True):
        call_command("enviar_recordatorios")

    cita.refresh_from_db()
    assert cita.recordatorio_enviado is True


@pytest.mark.django_db
def test_programador_una_vez(paciente, profesional):
    _factura(paciente, profesional)

    call_command("programador", "--una-vez")

    assert _avisos(paciente).count() == 1
