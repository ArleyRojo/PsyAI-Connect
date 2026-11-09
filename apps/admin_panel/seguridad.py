"""Configuración de seguridad (HU-13: cierre automático de sesión por inactividad)."""
from django.core.cache import cache

from apps.admin_panel.models import ConfiguracionSeguridad
from apps.admin_panel.repositories import AdminRepository

CACHE_MINUTOS = "psyai:minutos_inactividad"
AVISO_SEGUNDOS = 60
# El administrador no se desconecta por inactividad (decisión del equipo)
ROLES_EXENTOS = {"admin", "administrador"}


def minutos_inactividad():
    """Minutos sin actividad antes de cerrar la sesión (con caché de 60 s)."""
    minutos = cache.get(CACHE_MINUTOS)
    if minutos is None:
        minutos = ConfiguracionSeguridad.obtener().minutosInactividad
        cache.set(CACHE_MINUTOS, minutos, 60)
    return minutos


def aplica_a_rol(rol):
    return (rol or "").strip().lower() not in ROLES_EXENTOS


def info_para_usuario(rol):
    """Lo que necesita el navegador para su temporizador."""
    return {
        "success": True,
        "aplica": aplica_a_rol(rol),
        "minutos": minutos_inactividad(),
        "avisoSegundos": AVISO_SEGUNDOS,
    }, 200


def obtener_config():
    return {"success": True, "config": ConfiguracionSeguridad.obtener().to_dict()}, 200


def actualizar_config(data, administrador="Admin"):
    valor = (data or {}).get("minutosInactividad")
    try:
        minutos = int(valor)
        if str(valor).strip() != str(minutos):
            raise ValueError
    except (TypeError, ValueError):
        return {"success": False, "message": "Escribe un número entero de minutos."}, 400

    if not ConfiguracionSeguridad.MINUTOS_MIN <= minutos <= ConfiguracionSeguridad.MINUTOS_MAX:
        return {
            "success": False,
            "message": f"El tiempo debe estar entre {ConfiguracionSeguridad.MINUTOS_MIN} y "
                       f"{ConfiguracionSeguridad.MINUTOS_MAX} minutos.",
        }, 400

    config = ConfiguracionSeguridad.obtener()
    anterior = config.minutosInactividad
    config.minutosInactividad = minutos
    config.actualizadoPor = administrador
    config.save()
    cache.delete(CACHE_MINUTOS)

    if anterior != minutos:
        AdminRepository().registrar_log(
            modulo="Seguridad",
            accion="Actualizar cierre por inactividad",
            detalle=f"Tiempo de inactividad: de {anterior} a {minutos} minutos",
            administrador=administrador,
        )
    return {"success": True, "message": "Configuración guardada", "config": config.to_dict()}, 200
