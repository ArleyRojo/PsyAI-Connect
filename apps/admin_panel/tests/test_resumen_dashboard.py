"""Datos del dashboard admin rediseñado: actividad por hora y tendencias de 7 días."""
import json
from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.utils import timezone

from apps.admin_panel import resumen
from apps.admin_panel.models import Logs
from apps.authentication.models import Register
from apps.authentication.security import SecurityHelper
from apps.scheduling.models import Citas


def _usuario(email, rol, nombre="Usuario"):
    return Register.objects.create(
        nombre=nombre, email=email, contrasena=SecurityHelper.hash_password("Clave123*"),
        rol=rol, activo=True, estadoCuenta="Activa",
    )


def _log(dia, hora, modulo="usuarios"):
    log = Logs.objects.create(administrador="Admin", modulo=modulo, accion="Prueba", detalle="")
    momento = timezone.make_aware(datetime.combine(dia, time(hora, 15)))
    Logs.objects.filter(pk=log.pk).update(fecha=momento)


def test_actividad_por_hora_cuenta_solo_hoy():
    hoy = timezone.localdate()
    _log(hoy, 9)
    _log(hoy, 9)
    _log(hoy, 14)
    _log(hoy - timedelta(days=1), 9)

    horas = resumen.actividad_por_hora(hoy)

    assert len(horas) == 24
    assert horas[9] == 2 and horas[14] == 1
    assert sum(horas) == 3


def test_tendencias_de_7_dias():
    hoy = timezone.localdate()
    pac = _usuario("pac@test.com", "paciente")
    pro = _usuario("pro@test.com", "profesional")
    Register.objects.filter(pk=pac.pk).update(
        fechaRegistro=timezone.make_aware(datetime.combine(hoy - timedelta(days=2), time(10))))
    for dias, estado in [(0, "Pendiente"), (0, "Cancelada"), (3, "Completada"), (9, "Pendiente")]:
        Citas.objects.create(idPaciente=pac, idProfesional=pro, fecha=hoy - timedelta(days=dias),
                             hora=time(10), estado=estado)
    _log(hoy, 8, modulo="seguridad")
    _log(hoy - timedelta(days=6), 8, modulo="seguridad")
    _log(hoy - timedelta(days=7), 8, modulo="seguridad")  # fuera del rango

    t = resumen.tendencias(hoy)

    assert t["dias"][-1] == hoy.isoformat() and len(t["dias"]) == 7
    assert t["registros"] == [0, 0, 0, 0, 1, 0, 1]  # pac hace 2 días, pro hoy
    assert t["citas"] == [0, 0, 0, 1, 0, 0, 1]  # la cancelada y la de hace 9 días no cuentan
    assert t["seguridad"] == [1, 0, 0, 0, 0, 0, 1]
    assert resumen.citas_hoy(hoy) == 1


def test_stats_incluye_el_resumen(client):
    cache.clear()
    _usuario("admin@test.com", "admin", "Admin")
    r = client.post("/api/login", data=json.dumps({"email": "admin@test.com", "password": "Clave123*", "rol": "admin"}),
                    content_type="application/json")
    assert r.status_code == 200

    stats = client.get("/api/admin/stats").json()["stats"]

    assert len(stats["actividad_por_hora"]) == 24
    assert set(stats["tendencias"]) == {"dias", "registros", "citas", "seguridad"}
    assert "citas_hoy" in stats
    cache.clear()
