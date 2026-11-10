"""Pruebas de mantenimiento (HU-24) y copias de seguridad (HU-30 / HU-31)."""
import json
from datetime import time, timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone

from apps.admin_panel import copias, mantenimiento
from apps.admin_panel.models import ConfiguracionSistema, Logs
from apps.authentication.models import Register
from apps.authentication.security import SecurityHelper
from apps.scheduling.models import Notificaciones


@pytest.fixture(autouse=True)
def limpiar_cache():
    cache.clear()
    yield
    cache.clear()


def _usuario(email, rol, nombre="Usuario"):
    return Register.objects.create(
        nombre=nombre, email=email, contrasena=SecurityHelper.hash_password("Clave123*"),
        rol=rol, activo=True, estadoCuenta="Activa",
    )


def _login(client, email, rol):
    r = client.post("/api/login", data=json.dumps({"email": email, "password": "Clave123*", "rol": rol}),
                    content_type="application/json")
    assert r.status_code == 200


# ── Copias de seguridad ────────────────────────────────────────────────────
class TestCopias:
    def test_crea_copia_cifrada(self):
        _usuario("ana@test.com", "paciente", "Ana")

        payload, status = mantenimiento.crear_copia("Admin", "manual")

        assert status == 201
        archivo = Path(settings.BACKUP_DIR) / payload["copia"]["archivo"]
        contenido = archivo.read_bytes()
        assert b"ana@test.com" not in contenido  # está cifrada
        assert payload["copia"]["tipo"] == "Manual"
        assert Logs.objects.filter(modulo="Mantenimiento", accion="Crear copia de seguridad").exists()

    def test_restaurar_recupera_los_datos(self):
        _usuario("ana@test.com", "paciente", "Ana")
        copia = mantenimiento.crear_copia("Admin")[0]["copia"]
        Register.objects.filter(email="ana@test.com").update(nombre="Cambiado")
        _usuario("nuevo@test.com", "paciente", "Nuevo")

        payload, status = mantenimiento.restaurar_copia(
            {"archivo": copia["archivo"], "confirmacion": "RESTAURAR"}, "Admin")

        assert status == 200, payload
        assert Register.objects.get(email="ana@test.com").nombre == "Ana"
        assert not Register.objects.filter(email="nuevo@test.com").exists()
        # Se guardó el estado anterior y el log de la restauración sobrevive
        assert any(c["clave"] == "previa" for c in copias.listar())
        assert Logs.objects.filter(accion="Restaurar copia de seguridad").exists()

    def test_restaurar_no_toca_las_sesiones(self, client):
        _usuario("admin@test.com", "admin", "Admin")
        copia = mantenimiento.crear_copia("Admin")[0]["copia"]
        _login(client, "admin@test.com", "admin")
        sesiones = Session.objects.count()

        r = client.post("/api/admin/copias/restaurar",
                        data=json.dumps({"archivo": copia["archivo"], "confirmacion": "RESTAURAR"}),
                        content_type="application/json")

        assert r.status_code == 200
        assert Session.objects.count() == sesiones
        assert client.get("/api/admin/copias").status_code == 200  # sigue con sesión

    def test_restaurar_pide_escribir_restaurar(self):
        copia = mantenimiento.crear_copia("Admin")[0]["copia"]

        _, status = mantenimiento.restaurar_copia({"archivo": copia["archivo"], "confirmacion": "si"})

        assert status == 400

    def test_no_permite_rutas_raras(self):
        _, status = mantenimiento.restaurar_copia({"archivo": "../../settings.py", "confirmacion": "RESTAURAR"})

        assert status == 404

    def test_guarda_solo_las_ultimas_7(self):
        carpeta = Path(settings.BACKUP_DIR)
        carpeta.mkdir(parents=True, exist_ok=True)
        for dia in range(1, 9):
            (carpeta / f"psyai_202611{dia:02d}_020000_auto.psyai").write_bytes(b"x")

        mantenimiento.crear_copia("Admin")

        nombres = [c["archivo"] for c in copias.listar()]
        assert len(nombres) == 7
        assert "psyai_20261101_020000_auto.psyai" not in nombres

    def test_copia_automatica_una_vez_al_dia_a_la_hora(self):
        config = ConfiguracionSistema.obtener()
        config.horaCopia = (timezone.localtime() + timedelta(hours=1)).time().replace(second=0, microsecond=0)
        config.save()
        if config.horaCopia > timezone.localtime().time():  # (no aplica si son las 11 p. m.)
            assert "no toca" in mantenimiento.copia_automatica_si_toca()

        config.horaCopia = time(0, 0)
        config.save()
        assert "creada" in mantenimiento.copia_automatica_si_toca()
        assert "no toca" in mantenimiento.copia_automatica_si_toca()  # ya hay una hoy

    def test_cambiar_hora(self):
        _, status = mantenimiento.cambiar_hora_copia({"hora": "03:30"}, "Admin")
        assert status == 200
        assert ConfiguracionSistema.obtener().horaCopia == time(3, 30)
        assert mantenimiento.cambiar_hora_copia({"hora": "25:00"})[1] == 400

    def test_solo_el_admin(self, client):
        _usuario("pro@test.com", "profesional")
        _login(client, "pro@test.com", "profesional")

        assert client.post("/api/admin/copias").status_code == 403
        assert client.post("/api/admin/copias/restaurar", data="{}", content_type="application/json").status_code == 403


# ── Mantenimiento ──────────────────────────────────────────────────────────
class TestEstadoYAcciones:
    def test_estado_del_sistema(self):
        payload, status = mantenimiento.estado()

        assert status == 200
        assert payload["estado"]["baseDatos"]["estado"] == "ok"
        assert payload["estado"]["migraciones"]["estado"] == "ok"
        assert payload["estado"]["programador"]["estado"] == "error"  # nunca ha corrido

        mantenimiento.registrar_latido()
        assert mantenimiento.estado()[0]["estado"]["programador"]["estado"] == "ok"

    def test_limpiar_notificaciones_viejas(self):
        usuario = _usuario("ana@test.com", "paciente")
        vieja = Notificaciones.objects.create(idUsuario=usuario, titulo="Vieja", estado="enviado")
        Notificaciones.objects.filter(pk=vieja.pk).update(fecha=timezone.now() - timedelta(days=200))
        Notificaciones.objects.create(idUsuario=usuario, titulo="Nueva", estado="enviado")

        payload, status = mantenimiento.ejecutar_accion({"accion": "limpiar_notificaciones"}, "Admin")

        assert status == 200
        assert "1 notificación" in payload["message"]
        assert list(Notificaciones.objects.values_list("titulo", flat=True)) == ["Nueva"]
        assert Logs.objects.filter(modulo="Mantenimiento", accion="Limpiar notificaciones antiguas").exists()

    @pytest.mark.parametrize("accion", ["limpiar_sesiones", "limpiar_logs", "limpiar_cache", "recordatorios_citas",
                                        "recordatorios_cobro", "notificaciones_programadas"])
    def test_acciones(self, accion):
        _, status = mantenimiento.ejecutar_accion({"accion": accion}, "Admin")

        assert status == 200

    def test_accion_desconocida(self):
        assert mantenimiento.ejecutar_accion({"accion": "borrar_todo"})[1] == 400

    def test_probar_correo(self):
        from django.core import mail
        payload, status = mantenimiento.ejecutar_accion({"accion": "probar_correo"}, "Admin", "admin@test.com")

        assert status == 200
        assert mail.outbox[-1].to == ["admin@test.com"]


class TestModoMantenimiento:
    def test_bloquea_a_pacientes_y_no_al_admin(self, client):
        _usuario("pac@test.com", "paciente")
        _usuario("admin@test.com", "admin")
        mantenimiento.cambiar_modo({"activo": True, "mensaje": "Volvemos a las 3 p. m."}, "Admin")

        # Visitante: página de mantenimiento, pero el login sigue disponible
        r = client.get("/patient.dashboard.html")
        assert r.status_code == 503
        assert "Volvemos a las 3 p. m." in r.content.decode()
        assert client.get("/login.html").status_code == 200

        _login(client, "pac@test.com", "paciente")
        r = client.get("/api/paciente/consejos")
        assert r.status_code == 503
        assert r.json()["code"] == "maintenance"

        _login(client, "admin@test.com", "admin")
        assert client.get("/api/admin/mantenimiento").status_code == 200

        mantenimiento.cambiar_modo({"activo": False}, "Admin")
        _login(client, "pac@test.com", "paciente")
        assert client.get("/api/paciente/consejos").status_code == 200
        assert Logs.objects.filter(accion="Activar modo mantenimiento").exists()


def test_comando_copia_seguridad():
    call_command("copia_seguridad")

    assert len(copias.listar()) == 1
