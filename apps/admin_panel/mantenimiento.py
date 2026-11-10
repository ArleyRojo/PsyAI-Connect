"""
Mantenimiento del sistema (HU-24) y copias de seguridad (HU-30 / HU-31).
Toda acción queda registrada en Logs (módulo "Mantenimiento") para auditoría (RN-13).
"""
import io
import logging
import shutil
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from apps.admin_panel import copias
from apps.admin_panel.models import ConfiguracionSistema, Logs
from apps.admin_panel.repositories import AdminRepository

logger = logging.getLogger(__name__)

CACHE_MODO = "psyai:modo_mantenimiento"
DIAS_NOTIFICACIONES = 180   # se limpian las notificaciones de más de 6 meses
DIAS_LOGS = 365             # se limpian los logs de más de 1 año
MINUTOS_LATIDO = 10         # el programador se considera caído si no da señales en 10 min


def _log(accion, detalle, administrador):
    AdminRepository().registrar_log(modulo="Mantenimiento", accion=accion, detalle=detalle,
                                    administrador=administrador)


# ── Modo mantenimiento ─────────────────────────────────────────────────────
def modo_actual():
    """(activo, mensaje) con caché de 15 s (lo consulta el middleware en cada request)."""
    datos = cache.get(CACHE_MODO)
    if datos is None:
        config = ConfiguracionSistema.obtener()
        datos = (config.modoMantenimiento, config.mensajeMantenimiento)
        cache.set(CACHE_MODO, datos, 15)
    return datos


def cambiar_modo(data, administrador="Admin"):
    activo = (data or {}).get("activo")
    if not isinstance(activo, bool):
        return {"success": False, "message": "Valor no válido"}, 400
    mensaje = str((data or {}).get("mensaje") or "").strip()
    if len(mensaje) > 300:
        return {"success": False, "message": "El mensaje no puede superar 300 caracteres"}, 400

    config = ConfiguracionSistema.obtener()
    config.modoMantenimiento = activo
    if mensaje:
        config.mensajeMantenimiento = mensaje
    config.actualizadoPor = administrador
    config.save()
    cache.delete(CACHE_MODO)
    _log("Activar modo mantenimiento" if activo else "Desactivar modo mantenimiento",
         f"Mensaje: {config.mensajeMantenimiento}" if activo else "La plataforma vuelve a estar disponible",
         administrador)
    texto = ("Modo mantenimiento activado: pacientes y profesionales verán el aviso."
             if activo else "Modo mantenimiento desactivado: la plataforma está disponible.")
    return {"success": True, "message": texto, "config": config.to_dict()}, 200


# ── Estado del sistema ─────────────────────────────────────────────────────
def _tamano(num):
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            return f"{num:.0f} {unidad}" if unidad == "B" else f"{num:.1f} {unidad}"
        num /= 1024
    return f"{num:.1f} PB"


def _estado_bd():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            detalle = connection.vendor
            if connection.vendor == "postgresql":
                cursor.execute("SELECT pg_database_size(current_database())")
                detalle = f"PostgreSQL · {_tamano(cursor.fetchone()[0])}"
        return {"estado": "ok", "texto": "Conectada", "detalle": detalle}
    except Exception as e:
        return {"estado": "error", "texto": "Sin conexión", "detalle": str(e)[:150]}


def _estado_correo():
    backend = settings.EMAIL_BACKEND.rsplit(".", 1)[-1]
    if "console" in settings.EMAIL_BACKEND or "locmem" in settings.EMAIL_BACKEND:
        return {"estado": "aviso", "texto": "Modo desarrollo", "detalle": "Los correos se muestran en la consola"}
    if not getattr(settings, "EMAIL_HOST_USER", ""):
        return {"estado": "aviso", "texto": "Sin configurar", "detalle": f"{backend} sin usuario"}
    return {"estado": "ok", "texto": "Configurado", "detalle": f"{settings.EMAIL_HOST}:{settings.EMAIL_PORT}"}


def _estado_disco():
    uso = shutil.disk_usage(settings.BASE_DIR)
    porcentaje = round(uso.used / uso.total * 100)
    estado = "error" if porcentaje >= 95 else "aviso" if porcentaje >= 85 else "ok"
    return {"estado": estado, "texto": f"{porcentaje}% usado", "detalle": f"Libre: {_tamano(uso.free)}"}


def _estado_programador():
    latido = ConfiguracionSistema.obtener().programadorLatido
    if not latido:
        return {"estado": "error", "texto": "Sin señales", "detalle": "El servicio scheduler no ha arrancado"}
    if timezone.now() - latido > timedelta(minutes=MINUTOS_LATIDO):
        return {"estado": "error", "texto": "Detenido",
                "detalle": f"Última señal: {timezone.localtime(latido).strftime('%d/%m %H:%M')}"}
    return {"estado": "ok", "texto": "Funcionando",
            "detalle": f"Última señal: {timezone.localtime(latido).strftime('%H:%M')}"}


def _estado_migraciones():
    try:
        executor = MigrationExecutor(connection)
        pendientes = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if pendientes:
            return {"estado": "error", "texto": f"{len(pendientes)} pendiente(s)",
                    "detalle": "Reinicia el contenedor app para aplicarlas"}
        return {"estado": "ok", "texto": "Al día", "detalle": "Todas aplicadas"}
    except Exception as e:
        return {"estado": "error", "texto": "No se pudo revisar", "detalle": str(e)[:150]}


def _estado_copias():
    lista = copias.listar()
    if not lista:
        return {"estado": "aviso", "texto": "Sin copias", "detalle": "Crea la primera copia de seguridad"}
    ultima = datetime.fromisoformat(lista[0]["fecha"])
    estado = "ok" if timezone.now() - ultima < timedelta(hours=26) else "aviso"
    return {"estado": estado, "texto": f"{len(lista)} guardada(s)",
            "detalle": f"Última: {timezone.localtime(ultima).strftime('%d/%m %H:%M')}"}


def estado():
    config = ConfiguracionSistema.obtener()
    return {
        "success": True,
        "estado": {
            "baseDatos": _estado_bd(),
            "correo": _estado_correo(),
            "disco": _estado_disco(),
            "programador": _estado_programador(),
            "migraciones": _estado_migraciones(),
            "copias": _estado_copias(),
        },
        "config": config.to_dict(),
    }, 200


# ── Acciones ───────────────────────────────────────────────────────────────
def _comando(nombre):
    salida = io.StringIO()
    call_command(nombre, stdout=salida)
    return salida.getvalue().strip() or "Listo"


def _limpiar_sesiones():
    from django.contrib.sessions.models import Session
    borradas, _ = Session.objects.filter(expire_date__lt=timezone.now()).delete()
    return f"Se borraron {borradas} sesión(es) vencida(s)."


def _limpiar_notificaciones():
    from apps.scheduling.models import Notificaciones
    limite = timezone.now() - timedelta(days=DIAS_NOTIFICACIONES)
    borradas, _ = Notificaciones.objects.filter(fecha__lt=limite).exclude(estado="pendiente").delete()
    return f"Se borraron {borradas} notificación(es) de más de 6 meses."


def _limpiar_logs():
    limite = timezone.now() - timedelta(days=DIAS_LOGS)
    borrados, _ = Logs.objects.filter(fecha__lt=limite).delete()
    return f"Se borraron {borrados} log(s) de más de 1 año."


def _limpiar_cache():
    cache.clear()
    return "Se vació la caché."


ACCIONES = {
    "limpiar_sesiones": ("Limpiar sesiones vencidas", _limpiar_sesiones),
    "limpiar_notificaciones": ("Limpiar notificaciones antiguas", _limpiar_notificaciones),
    "limpiar_logs": ("Limpiar logs antiguos", _limpiar_logs),
    "limpiar_cache": ("Vaciar caché", _limpiar_cache),
    "recordatorios_citas": ("Ejecutar recordatorios de citas", lambda: _comando("enviar_recordatorios")),
    "recordatorios_cobro": ("Ejecutar recordatorios de cobro", lambda: _comando("enviar_recordatorios_cobro")),
    "notificaciones_programadas": ("Ejecutar notificaciones programadas",
                                   lambda: _comando("enviar_notificaciones_programadas")),
}


def ejecutar_accion(data, administrador="Admin", email_admin=None):
    accion = (data or {}).get("accion")
    if accion == "probar_correo":
        return _probar_correo(administrador, email_admin)
    if accion not in ACCIONES:
        return {"success": False, "message": "Acción no válida"}, 400
    nombre, funcion = ACCIONES[accion]
    try:
        resultado = funcion()
    except Exception as e:
        logger.exception("Error en la acción de mantenimiento %s", accion)
        _log(nombre, f"Falló: {e}", administrador)
        return {"success": False, "message": f"{nombre}: falló ({e})"}, 500
    _log(nombre, resultado, administrador)
    return {"success": True, "message": resultado}, 200


def _probar_correo(administrador, email_admin):
    if not email_admin:
        return {"success": False, "message": "Tu cuenta no tiene correo"}, 400
    try:
        send_mail("[PsyAI] Correo de prueba", "Si lees esto, el correo de PsyAI Connect funciona.",
                  settings.DEFAULT_FROM_EMAIL, [email_admin], fail_silently=False)
    except Exception as e:
        _log("Probar correo", f"Falló: {e}", administrador)
        return {"success": False, "message": f"No se pudo enviar: {e}"}, 500
    _log("Probar correo", f"Correo de prueba enviado a {email_admin}", administrador)
    return {"success": True, "message": f"Correo de prueba enviado a {email_admin}"}, 200


# ── Copias de seguridad ────────────────────────────────────────────────────
def listar_copias():
    return {
        "success": True,
        "copias": copias.listar(),
        "maxCopias": copias.MAX_COPIAS,
        "horaCopia": ConfiguracionSistema.obtener().to_dict()["horaCopia"],
    }, 200


def crear_copia(administrador="Admin", tipo="manual"):
    try:
        copia = copias.crear(tipo)
    except Exception as e:
        logger.exception("Error creando la copia de seguridad")
        _log("Crear copia de seguridad", f"Falló: {e}", administrador)
        return {"success": False, "message": f"No se pudo crear la copia: {e}"}, 500
    _log("Crear copia de seguridad", f"Copia {copias.TIPOS[tipo].lower()}: {copia['archivo']}", administrador)
    return {"success": True, "message": "Copia de seguridad creada", "copia": copia}, 201


def cambiar_hora_copia(data, administrador="Admin"):
    texto = str((data or {}).get("hora") or "").strip()
    try:
        hora = datetime.strptime(texto, "%H:%M").time()
    except ValueError:
        return {"success": False, "message": "Escribe la hora en formato HH:MM"}, 400
    config = ConfiguracionSistema.obtener()
    anterior = config.horaCopia.strftime("%H:%M")
    config.horaCopia = hora
    config.actualizadoPor = administrador
    config.save()
    _log("Cambiar hora de copia automática", f"De {anterior} a {texto}", administrador)
    return {"success": True, "message": f"La copia automática se hará todos los días a las {texto}",
            "horaCopia": texto}, 200


def restaurar_copia(data, administrador="Admin"):
    data = data or {}
    if str(data.get("confirmacion") or "").strip() != copias.CONFIRMACION:
        return {"success": False, "message": f"Escribe {copias.CONFIRMACION} para confirmar"}, 400
    nombre = data.get("archivo")
    if not any(c["archivo"] == nombre for c in copias.listar()):
        return {"success": False, "message": "Copia no encontrada"}, 404

    try:
        previa = copias.crear("previa")
    except Exception as e:
        logger.exception("No se pudo crear la copia previa")
        return {"success": False, "message": f"No se restauró: falló la copia del estado actual ({e})"}, 500

    try:
        copias.restaurar(nombre)
    except Exception as e:
        logger.exception("Error restaurando la copia %s", nombre)
        _log("Restaurar copia de seguridad", f"Falló al restaurar {nombre}: {e}. No se cambió nada.", administrador)
        return {"success": False, "message": f"No se pudo restaurar (no se cambió nada): {e}"}, 500

    cache.clear()
    # El log se escribe después de restaurar para que no lo borre la propia restauración
    _log("Restaurar copia de seguridad",
         f"Se restauró {nombre}. Copia del estado anterior: {previa['archivo']}", administrador)
    return {"success": True,
            "message": f"Datos restaurados. Por si acaso se guardó el estado anterior en {previa['archivo']}.",
            "previa": previa}, 200


def copia_automatica_si_toca():
    """La llama el programador cada 5 minutos: crea la copia del día cuando llega la hora."""
    config = ConfiguracionSistema.obtener()
    ahora = timezone.localtime()
    if ahora.time() < config.horaCopia or copias.hay_copia_automatica_hoy():
        return "Copia automática: no toca todavía"
    payload, status = crear_copia("Sistema", "auto")
    return payload["message"] if status != 201 else f"Copia automática creada: {payload['copia']['archivo']}"


def registrar_latido():
    ConfiguracionSistema.objects.filter(pk=ConfiguracionSistema.obtener().pk).update(programadorLatido=timezone.now())
