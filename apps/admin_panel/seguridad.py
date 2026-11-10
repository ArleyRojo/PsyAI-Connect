"""
Políticas de seguridad del sistema.
- HU-13: cierre automático de sesión por inactividad.
- HU-23: contraseñas, bloqueo por intentos fallidos y revisión periódica de las políticas (RN-13, RN-14).
"""
import re

from django.core.cache import cache
from django.utils import timezone

from apps.admin_panel.models import ConfiguracionSeguridad
from apps.admin_panel.repositories import AdminRepository

CACHE_MINUTOS = "psyai:minutos_inactividad"
CACHE_POLITICAS = "psyai:politicas_seguridad"
AVISO_SEGUNDOS = 60
# El administrador no se desconecta por inactividad (decisión del equipo)
ROLES_EXENTOS = {"admin", "administrador"}

# Campos numéricos y booleanos que el admin puede editar, con su nombre para el log
CAMPOS_NUMERICOS = {
    "minutosInactividad": "Tiempo de inactividad (minutos)",
    "passMinimo": "Largo mínimo de la contraseña",
    "intentosMaximos": "Intentos fallidos antes del bloqueo",
    "minutosBloqueo": "Minutos de bloqueo",
    "revisionMeses": "Revisión de políticas (meses)",
}
CAMPOS_BOOLEANOS = {
    "passMayuscula": "Exigir mayúscula",
    "passNumero": "Exigir número",
    "passSimbolo": "Exigir símbolo",
}


def _limpiar_cache():
    cache.delete(CACHE_MINUTOS)
    cache.delete(CACHE_POLITICAS)


def politicas():
    """Diccionario con las políticas vigentes (caché de 60 s)."""
    datos = cache.get(CACHE_POLITICAS)
    if datos is None:
        datos = ConfiguracionSeguridad.obtener().to_dict()
        cache.set(CACHE_POLITICAS, datos, 60)
    return datos


# ── HU-13: inactividad ─────────────────────────────────────────────────────
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


# ── HU-23: contraseñas y bloqueo ───────────────────────────────────────────
def requisitos_contrasena():
    """Texto y reglas de la política de contraseñas (también para mostrarlas en los formularios)."""
    p = politicas()
    partes = [f"al menos {p['passMinimo']} caracteres"]
    if p["passMayuscula"]:
        partes.append("una mayúscula")
    if p["passNumero"]:
        partes.append("un número")
    if p["passSimbolo"]:
        partes.append("un símbolo")
    texto = "La contraseña debe tener " + ", ".join(partes[:-1]) + (" y " if len(partes) > 1 else "") + partes[-1] + "."
    return {
        "minimo": p["passMinimo"],
        "mayuscula": p["passMayuscula"],
        "numero": p["passNumero"],
        "simbolo": p["passSimbolo"],
        "texto": texto,
    }


def validar_contrasena(password):
    """Devuelve el mensaje de error si la contraseña no cumple la política, o None si cumple."""
    p = politicas()
    password = password or ""
    if len(password) < p["passMinimo"]:
        return f"La contraseña debe tener al menos {p['passMinimo']} caracteres"
    if p["passMayuscula"] and not re.search(r"[A-Z]", password):
        return "La contraseña debe contener al menos una mayúscula"
    if p["passNumero"] and not re.search(r"[0-9]", password):
        return "La contraseña debe contener al menos un número"
    if p["passSimbolo"] and not re.search(r"[^A-Za-z0-9]", password):
        return "La contraseña debe contener al menos un símbolo (por ejemplo ! @ # $ *)"
    return None


def bloqueo():
    """(intentos permitidos, minutos de bloqueo)."""
    p = politicas()
    return p["intentosMaximos"], p["minutosBloqueo"]


# ── API del admin ──────────────────────────────────────────────────────────
def obtener_config():
    return {"success": True, "config": ConfiguracionSeguridad.obtener().to_dict()}, 200


def _texto_valor(valor):
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    return str(valor)


def actualizar_config(data, administrador="Admin"):
    data = data or {}
    cambios = {}

    for campo in CAMPOS_NUMERICOS:
        if campo not in data:
            continue
        valor = data.get(campo)
        try:
            numero = int(valor)
            if str(valor).strip() != str(numero):
                raise ValueError
        except (TypeError, ValueError):
            return {"success": False, "message": f"{CAMPOS_NUMERICOS[campo]}: escribe un número entero."}, 400
        minimo, maximo = ConfiguracionSeguridad.RANGOS[campo]
        if not minimo <= numero <= maximo:
            if campo == "minutosInactividad":
                mensaje = f"El tiempo debe estar entre {minimo} y {maximo} minutos."
            else:
                mensaje = f"{CAMPOS_NUMERICOS[campo]}: debe estar entre {minimo} y {maximo}."
            return {"success": False, "message": mensaje}, 400
        cambios[campo] = numero

    for campo in CAMPOS_BOOLEANOS:
        if campo not in data:
            continue
        valor = data.get(campo)
        if not isinstance(valor, bool):
            return {"success": False, "message": f"{CAMPOS_BOOLEANOS[campo]}: valor no válido."}, 400
        cambios[campo] = valor

    if not cambios:
        return {"success": False, "message": "No hay cambios para guardar."}, 400

    config = ConfiguracionSeguridad.obtener()
    detalles = []
    for campo, nuevo in cambios.items():
        anterior = getattr(config, campo)
        if anterior != nuevo:
            nombre = CAMPOS_NUMERICOS.get(campo) or CAMPOS_BOOLEANOS.get(campo)
            if campo == "minutosInactividad":
                detalles.append(f"Tiempo de inactividad: de {anterior} a {nuevo} minutos")
            else:
                detalles.append(f"{nombre}: de {_texto_valor(anterior)} a {_texto_valor(nuevo)}")
            setattr(config, campo, nuevo)
    config.actualizadoPor = administrador
    config.save()
    _limpiar_cache()

    if detalles:
        AdminRepository().registrar_log(
            modulo="Seguridad",
            accion="Actualizar cierre por inactividad" if list(cambios) == ["minutosInactividad"]
            else "Actualizar políticas de seguridad",
            detalle="; ".join(detalles),
            administrador=administrador,
        )
    return {"success": True, "message": "Configuración guardada", "config": config.to_dict()}, 200


def marcar_revisadas(administrador="Admin"):
    """El admin confirma que revisó las políticas (RN-14): reinicia el plazo de revisión."""
    config = ConfiguracionSeguridad.obtener()
    config.fechaUltimaRevision = timezone.now()
    config.revisadoPor = administrador
    config.save()
    _limpiar_cache()
    proxima = config.proxima_revision()
    AdminRepository().registrar_log(
        modulo="Seguridad",
        accion="Revisar políticas de seguridad",
        detalle=f"Políticas revisadas. Próxima revisión: {timezone.localtime(proxima).strftime('%d/%m/%Y')}",
        administrador=administrador,
    )
    return {"success": True, "message": "Políticas marcadas como revisadas", "config": config.to_dict()}, 200
