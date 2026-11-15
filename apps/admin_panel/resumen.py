"""
Datos del dashboard del admin que salen de la base (no de la memoria del servidor).
"""
from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.admin_panel.repositories import AdminRepository
from apps.authentication.repositories import AuthRepository
from apps.scheduling.repositories import AppointmentRepository

DIAS_TENDENCIA = 7


def _inicio_del_dia(dia):
    return timezone.make_aware(datetime.combine(dia, time.min))


def actividad_por_hora(hoy=None):
    hoy = hoy or timezone.localdate()
    inicio = _inicio_del_dia(hoy)
    filas = AdminRepository().get_activity_counts_by_hour(inicio, inicio + timedelta(days=1))
    horas = [0] * 24
    for fila in filas:
        if fila["hora"] is not None:
            horas[int(fila["hora"])] = fila["total"]
    return horas


def _conteos_por_dia(filas, dias):
    conteo = {fila["dia"]: fila["total"] for fila in filas}
    return [conteo.get(dia, 0) for dia in dias]


def tendencias(hoy=None):
    hoy = hoy or timezone.localdate()
    dias = [hoy - timedelta(days=n) for n in range(DIAS_TENDENCIA - 1, -1, -1)]
    inicio = _inicio_del_dia(dias[0])
    fin = _inicio_del_dia(dias[-1]) + timedelta(days=1)
    citas = AppointmentRepository().get_appointment_counts_by_day(dias[0], hoy)
    return {
        "dias": [dia.isoformat() for dia in dias],
        "registros": _conteos_por_dia(AuthRepository().get_registration_counts_by_day(inicio, fin), dias),
        "citas": [next((row["total"] for row in citas if row["fecha"] == dia), 0) for dia in dias],
        "seguridad": _conteos_por_dia(AdminRepository().get_log_counts_by_day(inicio, fin, module="seguridad"), dias),
    }


def citas_hoy(hoy=None):
    return AppointmentRepository().count_appointments_for_day(hoy or timezone.localdate())


def resumen():
    return {
        "actividad_por_hora": actividad_por_hora(),
        "tendencias": tendencias(),
        "citas_hoy": citas_hoy(),
    }