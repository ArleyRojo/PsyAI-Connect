"""Pruebas del cierre automático de sesión por inactividad (HU-13)."""
import json
import time

import pytest
from django.core.cache import cache

from apps.admin_panel import seguridad
from apps.admin_panel.models import ConfiguracionSeguridad, Logs
from apps.authentication.models import Register
from apps.authentication.security import SecurityHelper


@pytest.fixture(autouse=True)
def limpiar_cache():
    cache.delete(seguridad.CACHE_MINUTOS)
    yield
    cache.delete(seguridad.CACHE_MINUTOS)


def _usuario(email, rol):
    return Register.objects.create(
        nombre=f"Usuario {rol}", email=email, contrasena=SecurityHelper.hash_password("Clave123*"),
        rol=rol, activo=True, estadoCuenta="Activa",
    )


def _login(client, email, rol):
    r = client.post("/api/login", data=json.dumps({"email": email, "password": "Clave123*", "rol": rol}),
                    content_type="application/json")
    assert r.status_code == 200


def _inactivo_hace(client, minutos):
    sesion = client.session
    sesion["ultimaActividad"] = int(time.time()) - minutos * 60
    sesion.save()


@pytest.mark.django_db
class TestConfiguracion:
    def test_valor_por_defecto_es_15_minutos(self):
        assert seguridad.minutos_inactividad() == 15

    def test_actualizar_guarda_y_registra_log(self):
        payload, status = seguridad.actualizar_config({"minutosInactividad": 30}, administrador="Admin Test")

        assert status == 200
        assert payload["config"]["minutosInactividad"] == 30
        assert seguridad.minutos_inactividad() == 30
        log = Logs.objects.get(modulo="Seguridad")
        assert "de 15 a 30 minutos" in log.detalle
        assert log.administrador == "Admin Test"

    @pytest.mark.parametrize("valor", [4, 121, "abc", "10.5", None, ""])
    def test_valores_invalidos(self, valor):
        _, status = seguridad.actualizar_config({"minutosInactividad": valor})

        assert status == 400
        assert ConfiguracionSeguridad.obtener().minutosInactividad == 15


@pytest.mark.django_db
class TestCierrePorInactividad:
    def test_paciente_activo_sigue_conectado(self, client):
        _usuario("pac@test.com", "paciente")
        _login(client, "pac@test.com", "paciente")
        _inactivo_hace(client, 10)

        r = client.get("/api/sesion/inactividad")

        assert r.status_code == 200
        assert r.json() == {"success": True, "aplica": True, "minutos": 15, "avisoSegundos": 60}

    def test_paciente_inactivo_pierde_la_sesion(self, client):
        _usuario("pac@test.com", "paciente")
        _login(client, "pac@test.com", "paciente")
        _inactivo_hace(client, 16)

        r = client.get("/api/sesion/inactividad")

        assert r.status_code == 401
        assert "idUsuario" not in client.session

    def test_profesional_inactivo_pierde_la_sesion(self, client):
        _usuario("pro@test.com", "profesional")
        _login(client, "pro@test.com", "profesional")
        _inactivo_hace(client, 16)

        assert client.get("/api/sesion/inactividad").status_code == 401

    def test_respeta_el_tiempo_configurado(self, client):
        seguridad.actualizar_config({"minutosInactividad": 30})
        _usuario("pac@test.com", "paciente")
        _login(client, "pac@test.com", "paciente")
        _inactivo_hace(client, 20)

        r = client.get("/api/sesion/inactividad")

        assert r.status_code == 200
        assert r.json()["minutos"] == 30

    def test_admin_no_se_desconecta(self, client):
        _usuario("admin@test.com", "admin")
        _login(client, "admin@test.com", "admin")
        _inactivo_hace(client, 60)

        r = client.get("/api/sesion/inactividad")

        assert r.status_code == 200
        assert r.json()["aplica"] is False


@pytest.mark.django_db
class TestApiAdmin:
    def test_solo_el_admin_cambia_la_configuracion(self, client):
        _usuario("pac@test.com", "paciente")
        _login(client, "pac@test.com", "paciente")
        assert client.put("/api/admin/seguridad", data=json.dumps({"minutosInactividad": 30}),
                          content_type="application/json").status_code == 403

        _usuario("admin@test.com", "admin")
        _login(client, "admin@test.com", "admin")
        r = client.put("/api/admin/seguridad", data=json.dumps({"minutosInactividad": 30}),
                       content_type="application/json")
        assert r.status_code == 200
        assert client.get("/api/admin/seguridad").json()["config"]["minutosInactividad"] == 30
