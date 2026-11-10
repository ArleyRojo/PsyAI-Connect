"""
Datos del dashboard del admin que salen de la base (no de la memoria del servidor),
así no se pierden si se reinicia:

- Actividad por hora de hoy: acciones registradas en Logs, agrupadas por hora (24 valores).
- Tendencias de los últimos 7 días: registros nuevos, citas por día y eventos de seguridad.
- Citas de hoy (sin contar las canceladas).

Las horas y los días son los de Colombia (TIME_ZONE).
"""
from datetime import datetime, time, timedelta

from django.db.models import Count
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone

from apps.admin_panel.models import Logs
from apps.authentication.models import Register

DIAS_TENDENCIA = 7


def _inicio_del_dia(dia):
    return timezone.make_aware(datetime.combine(dia, time.min))


def actividad_por_hora(hoy=None):
    """Lista de 24 números: acciones registradas en cada hora de hoy."""
    hoy = hoy or timezone.localdate()
    inicio = _inicio_del_dia(hoy)
    filas = (
        Logs.objects.filter(fecha__gte=inicio, fecha__lt=inicio + timedelta(days=1))
        .annotate(hora=ExtractHour("fecha"))
        .values("hora")
        .annotate(total=Count("pk"))
    )
    horas = [0] * 24
    for fila in filas:
        if fila["hora"] is not None:
            horas[int(fila["hora"])] = fila["total"]
    return horas


def _por_dia(queryset, campo, dias):
    """Cuenta filas por día (fecha local) para la lista de días dada."""
    inicio = _inicio_del_dia(dias[0])
    fin = _inicio_del_dia(dias[-1]) + timedelta(days=1)
    filas = (
        queryset.filter(**{f"{campo}__gte": inicio, f"{campo}__lt": fin})
        .annotate(dia=TruncDate(campo))
        .values("dia")
        .annotate(total=Count("pk"))
    )
    conteo = {f["dia"]: f["total"] for f in filas}
    return [conteo.get(d, 0) for d in dias]


def tendencias(hoy=None):
    """Series de los últimos 7 días (del más viejo a hoy)."""
    from apps.scheduling.models import Citas

    hoy = hoy or timezone.localdate()
    dias = [hoy - timedelta(days=n) for n in range(DIAS_TENDENCIA - 1, -1, -1)]

    citas = (
        Citas.objects.filter(fecha__gte=dias[0], fecha__lte=hoy)
        .exclude(estado="Cancelada")
        .values("fecha")
        .annotate(total=Count("pk"))
    )
    citas_dia = {c["fecha"]: c["total"] for c in citas}

    return {
        "dias": [d.isoformat() for d in dias],
        "registros": _por_dia(Register.objects.all(), "fechaRegistro", dias),
        "citas": [citas_dia.get(d, 0) for d in dias],
        "seguridad": _por_dia(Logs.objects.filter(modulo="seguridad"), "fecha", dias),
    }


def citas_hoy(hoy=None):
    from apps.scheduling.models import Citas

    hoy = hoy or timezone.localdate()
    return Citas.objects.filter(fecha=hoy).exclude(estado="Cancelada").count()


def resumen():
    """Lo que se agrega a /api/admin/stats."""
    return {
        "actividad_por_hora": actividad_por_hora(),
        "tendencias": tendencias(),
        "citas_hoy": citas_hoy(),
    }
