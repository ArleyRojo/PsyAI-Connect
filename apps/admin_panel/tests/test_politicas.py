"""Pruebas de las políticas de seguridad configurables (HU-23)."""
import json
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.admin_panel import seguridad
from apps.admin_panel.models import ConfiguracionSeguridad, Logs
from apps.authentication.models import Register
from apps.authentication.repositories import SecurityRepository
from apps.authentication.security import SecurityHelper


@pytest.fixture(autouse=True)
def limpiar_cache():
    cache.clear()
    yield
    cache.clear()


def _registro(client, password):
    return client.post("/api/register", data=json.dumps({
        "nombre": "Nuevo Usuario", "email": "nuevo@test.com", "password": password, "confirm_password": password,
        "genero": "Otro", "fecha_nacimiento": "1995-05-05", "acepta_terminos": True,
    }), content_type="application/json")


@pytest.mark.django_db
class TestContrasenas:
    def test_por_defecto_son_las_reglas_de_siempre(self):
        assert seguridad.validar_contrasena("Abc123") is None
        assert seguridad.validar_contrasena("abc123") == "La contraseña debe contener al menos una mayúscula"

    def test_el_admin_endurece_la_politica(self):
        seguridad.actualizar_config({"passMinimo": 10, "passSimbolo": True}, "Admin Demo")

        assert "al menos 10 caracteres" in seguridad.validar_contrasena("Abc123")
        assert "símbolo" in seguridad.validar_contrasena("Abcdefgh123")
        assert seguridad.validar_contrasena("Abcdefgh12!") is None
        assert seguridad.requisitos_contrasena()["texto"] == (
            "La contraseña debe tener al menos 10 caracteres, una mayúscula, un número y un símbolo."
        )

    def test_el_registro_usa_la_politica(self, client):
        seguridad.actualizar_config({"passMinimo": 10})

        r = _registro(client, "Abc12345")

        assert r.status_code == 400
        assert "10 caracteres" in r.json()["message"]

    def test_endpoint_publico(self, client):
        r = client.get("/api/politicas/contrasena")

        assert r.status_code == 200
        assert r.json()["minimo"] == 6


@pytest.mark.django_db
class TestBloqueo:
    def test_usa_los_intentos_y_minutos_configurados(self):
        seguridad.actualizar_config({"intentosMaximos": 3, "minutosBloqueo": 30})
        repo = SecurityRepository()
        for _ in range(3):
            repo.register_failed_attempt("x@test.com")

        bloqueado, segundos = repo.check_brute_force("x@test.com")

        assert bloqueado is True
        assert 29 * 60 < segundos <= 30 * 60


@pytest.mark.django_db
class TestCambiosYRevision:
    @pytest.mark.parametrize("datos", [{"passMinimo": 5}, {"intentosMaximos": 11}, {"revisionMeses": 0},
                                       {"passSimbolo": "si"}, {}])
    def test_valores_invalidos(self, datos):
        _, status = seguridad.actualizar_config(datos)

        assert status == 400

    def test_cada_cambio_queda_en_logs(self):
        seguridad.actualizar_config({"passMinimo": 8, "passSimbolo": True}, "Admin Demo")

        log = Logs.objects.get(modulo="Seguridad")
        assert log.accion == "Actualizar políticas de seguridad"
        assert "Largo mínimo de la contraseña: de 6 a 8" in log.detalle
        assert "Exigir símbolo: de No a Sí" in log.detalle

    def test_revision_periodica(self):
        config = ConfiguracionSeguridad.obtener()
        assert config.revision_vencida() is True  # nunca revisadas

        payload, status = seguridad.marcar_revisadas("Admin Demo")

        assert status == 200
        assert payload["config"]["revisionVencida"] is False
        config.refresh_from_db()
        config.fechaUltimaRevision = timezone.now() - timedelta(days=200)
        config.save()
        assert config.revision_vencida() is True  # 6 meses por defecto
        assert Logs.objects.filter(accion="Revisar políticas de seguridad").exists()

    def test_api_revisar_solo_admin(self, client):
        Register.objects.create(nombre="Admin", email="admin@test.com", rol="admin", activo=True, estadoCuenta="Activa",
                                contrasena=SecurityHelper.hash_password("Clave123*"))
        assert client.post("/api/admin/seguridad/revisar").status_code in (401, 403)
        client.post("/api/login", data=json.dumps({"email": "admin@test.com", "password": "Clave123*", "rol": "admin"}),
                    content_type="application/json")
        assert client.post("/api/admin/seguridad/revisar").status_code == 200
