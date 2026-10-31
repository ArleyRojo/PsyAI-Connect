import json
import logging
import re

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_ROLES = frozenset({"admin", "profesional", "paciente"})

_SKIP_PREFIXES = (
    "/api/admin/usuarios",
    "/api/admin/roles",
    "/api/admin/notificaciones",
    "/api/admin/chatbot-config",
    "/api/admin/logs",
    "/api/admin/stats",
    "/api/admin/online",
    "/api/admin/chatbot-historial",
    "/api/client-errors",
    "/api/csrf",
    "/api/session",
    "/api/theme",
    "/api/newsletter",
    "/api/whatsapp",
)
_SKIP_EXACT = {"/api/chatbot", "/api/chatbot/enviar"}
_AUTH_BODY_PATHS = {"/api/login", "/api/register", "/api/forgot-password"}

_ANAMNESIS_RE = re.compile(r"^/api/paciente/\d+/anamnesis/?$")
_CITA_DETAIL_RE = re.compile(r"^/api/citas/\d+/?$")
_PROFESIONAL_DOCUMENTOS_RE = re.compile(r"^/api/profesional/pacientes/\d+/documentos/?$")
_PROFESIONAL_ASIGNAR_RE = re.compile(r"^/api/profesional/pacientes/\d+/asignar/?$")
_PROFESIONAL_VERIFICAR_RE = re.compile(r"^/api/admin/profesionales/\d+/(verificar|desverificar)/?$")
_DOCUMENTO_DETALLE_RE = re.compile(r"^/api/(?:paciente/documentos|documentos/paciente/doc)/\d+/?$")
_DOCUMENTO_PROFESIONAL_RE = re.compile(r"^/api/(?:profesional/documentos|documentos/profesional/doc)/\d+/?$")
_FACTURA_ACCION_RE = re.compile(r"^/api/facturas/\d+/(evidencia|confirmar-pago)/?$")


def _actor_from_session(session):
    if session is None:
        return None
    try:
        user_id = session.get("idUsuario")
        if not user_id:
            return None
        return {
            "id": user_id,
            "nombre": session.get("nombre") or f"Usuario #{user_id}",
            "rol": session.get("rol") or "",
        }
    except Exception:
        return None


def _client_ip(request):
    ip = (
        request.META.get("HTTP_X_FORWARDED_FOR")
        or request.META.get("HTTP_X_REAL_IP")
        or request.META.get("REMOTE_ADDR")
        or "desconocida"
    )
    if "," in ip:
        ip = ip.split(",")[0].strip()
    return ip[:50]


def _request_data(request):
    cached = getattr(request, "_audit_payload", None)
    if cached is not None:
        return cached
    try:
        data = request.data
        if hasattr(data, "dict"):
            return data.dict()
        return data or {}
    except Exception:
        try:
            return request.POST
        except Exception:
            return {}


def _mask_email(email):
    email = str(email or "").strip()
    if not email:
        return "desconocido"
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{local[:1]}***@{domain}"


def _role_origin(role):
    role = (role or "").lower()
    return role if role in _ROLES else "sistema"


def _classify_download(path):
    if path.startswith("/api/descargar/") or path.endswith("/descargar"):
        return "documentos", "Descargar documento"
    if path == "/api/paciente/mis-datos":
        return "cuenta", "Exportar datos personales"
    return None


def _classify(method, path):
    if path in ("/api/perfil/paciente/foto", "/api/perfil/foto"):
        return "perfil", "Actualizar foto de perfil"
    if path.startswith("/api/perfil/paciente"):
        return "perfil", "Actualizar perfil"
    if path.startswith("/api/perfil/profesional"):
        return "perfil", "Actualizar perfil profesional"
    if path.startswith("/api/preferencias/paciente"):
        return "perfil", "Actualizar preferencias"
    if path.startswith("/api/evolucion"):
        return "evolucion", "Guardar evolucion"
    if _ANAMNESIS_RE.match(path):
        return {
            "POST": ("anamnesis", "Registrar anamnesis"),
            "PUT": ("anamnesis", "Actualizar anamnesis"),
            "PATCH": ("anamnesis", "Actualizar anamnesis"),
            "DELETE": ("anamnesis", "Eliminar anamnesis"),
        }.get(method)
    if path.startswith("/api/diagnosticos"):
        return "diagnosticos", "Guardar diagnostico"
    if path.startswith("/api/reportes"):
        return {
            "POST": ("reportes", "Generar reporte"),
            "PUT": ("reportes", "Actualizar reporte"),
            "PATCH": ("reportes", "Actualizar reporte"),
            "DELETE": ("reportes", "Eliminar reporte"),
        }.get(method)
    if _PROFESIONAL_ASIGNAR_RE.match(path):
        return "pacientes", "Asignar paciente"
    if _PROFESIONAL_VERIFICAR_RE.match(path):
        accion = "Verificar profesional" if path.endswith("/verificar") else "Desverificar profesional"
        return "profesionales", accion
    if _PROFESIONAL_DOCUMENTOS_RE.match(path):
        return "documentos", "Subir documento clinico"
    if _DOCUMENTO_PROFESIONAL_RE.match(path):
        return {
            "PUT": ("documentos", "Actualizar documento clinico"),
            "PATCH": ("documentos", "Actualizar documento clinico"),
            "DELETE": ("documentos", "Eliminar documento clinico"),
        }.get(method)
    if path.startswith("/api/documentos/profesional/") and method == "POST":
        return "documentos", "Subir documento clinico"
    if _DOCUMENTO_DETALLE_RE.match(path):
        return {
            "PUT": ("documentos", "Actualizar documento"),
            "PATCH": ("documentos", "Actualizar documento"),
            "DELETE": ("documentos", "Eliminar documento"),
        }.get(method)
    if path.startswith("/api/profesional/documentos/"):
        return {
            "PUT": ("documentos", "Actualizar documento clinico"),
            "PATCH": ("documentos", "Actualizar documento clinico"),
            "DELETE": ("documentos", "Eliminar documento clinico"),
        }.get(method)
    if path.startswith("/api/paciente/documentos") and method == "POST":
        return "documentos", "Subir documento"
    if path.startswith("/api/documentos/paciente") and method == "POST":
        return "documentos", "Subir documento"
    if path.startswith("/api/documentos/autorizacion/"):
        return "documentos", "Actualizar autorizacion de documento"
    if path.startswith("/api/paciente/consentimiento-chatbot"):
        return "consentimiento", "Actualizar consentimiento del chatbot"
    if path.startswith("/api/paciente/consentimientos/revocar"):
        return "consentimiento", "Revocar consentimiento"
    if path.startswith("/api/cuenta/eliminar"):
        return "cuenta", "Solicitar eliminacion de cuenta"
    if path.startswith("/api/chatbot/encuesta"):
        return "chatbot", "Registrar encuesta de chatbot"
    if path.startswith("/api/chatbot/config"):
        return "chatbot", "Actualizar configuracion del chatbot"
    if path.startswith("/api/chatbot/prediagnostico"):
        return "chatbot", "Generar prediagnostico"
    if path.startswith("/api/chat/historial") and method == "DELETE":
        return "chat", "Eliminar historial de chat"
    if path in (
        "/api/chat/mensajes",
        "/api/chat/enviar",
        "/api/paciente/chat/mensajes",
        "/api/paciente/chat/enviar",
        "/api/profesional/chat/mensajes",
        "/api/profesional/chat/enviar",
    ) and method == "POST":
        return "chat", "Enviar mensaje"
    if path == "/api/disponibilidad" and method == "POST":
        return "agenda", "Crear disponibilidad"
    if path == "/api/citas" and method == "POST":
        return "citas", "Agendar cita"
    if _CITA_DETAIL_RE.match(path):
        return {
            "PUT": ("citas", "Actualizar cita"),
            "PATCH": ("citas", "Actualizar cita"),
            "DELETE": ("citas", "Cancelar cita"),
        }.get(method)
    if path.startswith("/api/profesional/payment-info"):
        return "pagos", "Actualizar informacion de pago"
    if _FACTURA_ACCION_RE.match(path):
        accion = "Subir evidencia de pago" if path.endswith("/evidencia") else "Confirmar pago"
        return "facturacion", accion
    return None


def _fallback(method, path):
    parts = [p for p in path.split("/") if p]
    modulo = parts[1] if len(parts) > 1 else "sistema"
    accion = {
        "POST": "Crear",
        "PUT": "Actualizar",
        "PATCH": "Actualizar",
        "DELETE": "Eliminar",
    }.get(method, "Accion")
    return modulo, accion


def registrar_log(
    modulo,
    accion,
    detalle,
    administrador="Sistema",
    origen="sistema",
    usuario_afectado=None,
    rol_anterior=None,
    rol_nuevo=None,
):
    try:
        from apps.admin_panel.repositories import AdminRepository

        AdminRepository().registrar_log(
            modulo,
            accion,
            detalle,
            rol_anterior=rol_anterior,
            rol_nuevo=rol_nuevo,
            usuario_afectado=usuario_afectado,
            administrador=administrador,
            origen=origen,
        )
    except Exception:
        logger.exception("No se pudo registrar el log de auditoria")


def registrar_acceso(usuario_id, accion, ip):
    try:
        from apps.admin_panel.models import AuditoriaAccesos
        from apps.admin_panel.repositories import AdminRepository

        AuditoriaAccesos.objects.create(
            idUsuario_id=usuario_id,
            accion=accion,
            ip=ip,
        )
        AdminRepository.increment_logs_version()
    except Exception:
        logger.exception("No se pudo registrar el acceso de auditoria")


class AuditActivityMiddleware(MiddlewareMixin):
    """Registra en el panel admin las acciones clave de pacientes y profesionales."""

    def process_request(self, request):
        request._audit_actor = _actor_from_session(getattr(request, "session", None))
        if request.path in _AUTH_BODY_PATHS and request.method == "POST":
            try:
                raw = request.body
                if raw and len(raw) <= 10240:
                    request._audit_payload = json.loads(raw.decode("utf-8"))
            except Exception:
                request._audit_payload = {}
        return None

    def process_response(self, request, response):
        try:
            self._process(request, response)
        except Exception:
            logger.exception(
                "Fallo al auditar la peticion %s %s", request.method, request.path
            )
        return response

    def _process(self, request, response):
        path = request.path
        if not path.startswith("/api/"):
            return

        method = request.method.upper()
        status = response.status_code
        ip = _client_ip(request)
        actor = getattr(request, "_audit_actor", None) or _actor_from_session(
            getattr(request, "session", None)
        )

        if path == "/api/login" and method == "POST":
            self._audit_login(request, status, ip, actor)
            return
        if path == "/api/logout" and method == "POST":
            if actor and 200 <= status < 300:
                registrar_acceso(actor["id"], "Cierre de sesion", ip)
            return
        if path == "/api/register" and method == "POST":
            self._audit_register(request, status, ip)
            return
        if path == "/api/totp/verify-login" and method == "POST":
            if 200 <= status < 300 and actor:
                registrar_acceso(actor["id"], "Inicio de sesion (2FA)", ip)
            elif status == 401:
                registrar_log(
                    "seguridad",
                    "Token invalido",
                    f"IP: {ip}",
                    administrador="Sistema",
                    origen="sistema",
                )
            return
        if path == "/api/totp/setup" and method in ("GET", "POST"):
            if 200 <= status < 300:
                self._log_actor(actor, ip, "seguridad", "Configurar 2FA", method, path)
            return
        if path == "/api/totp/confirm" and method == "POST":
            if 200 <= status < 300:
                self._log_actor(actor, ip, "seguridad", "Activar 2FA", method, path)
            return
        if path == "/api/totp/disable" and method == "POST":
            if 200 <= status < 300:
                self._log_actor(actor, ip, "seguridad", "Desactivar 2FA", method, path)
            return
        if path == "/api/forgot-password" and method == "POST":
            if 200 <= status < 300:
                data = _request_data(request)
                registrar_log(
                    "seguridad",
                    "Solicitud de recuperacion",
                    f"Email: {_mask_email(data.get('email'))} | IP: {ip}",
                    administrador="Sistema",
                    origen="sistema",
                )
            return
        if path == "/api/reset-password" and method == "POST":
            if 200 <= status < 300:
                registrar_log(
                    "seguridad",
                    "Contrasena restablecida",
                    f"IP: {ip}",
                    administrador="Sistema",
                    origen="sistema",
                )
            return
        if path == "/api/verify-email" and method == "POST":
            if 200 <= status < 300:
                registrar_log(
                    "seguridad",
                    "Correo verificado",
                    f"IP: {ip}",
                    administrador="Sistema",
                    origen="sistema",
                )
            return

        if path in _SKIP_EXACT or any(path.startswith(p) for p in _SKIP_PREFIXES):
            return

        if method in _SAFE_METHODS:
            if 200 <= status < 300:
                classification = _classify_download(path)
                if classification:
                    modulo, accion = classification
                    self._log_actor(actor, ip, modulo, accion, method, path)
            return

        if not 200 <= status < 300:
            return

        modulo, accion = _classify(method, path) or _fallback(method, path)
        self._log_actor(actor, ip, modulo, accion, method, path)

    def _audit_login(self, request, status, ip, actor):
        if 200 <= status < 300:
            if actor:
                registrar_acceso(actor["id"], "Inicio de sesion", ip)
            return
        if status in (401, 403, 429):
            data = _request_data(request)
            accion = "Rate limit login" if status == 429 else "Login fallido"
            registrar_log(
                "seguridad",
                accion,
                f"Email: {_mask_email(data.get('email'))} | IP: {ip}",
                administrador="Sistema",
                origen="sistema",
            )

    def _audit_register(self, request, status, ip):
        if not 200 <= status < 300:
            return
        data = _request_data(request)
        rol = (data.get("rol") or "paciente").lower()
        registrar_log(
            "usuarios",
            "Registro de cuenta",
            f"Email: {_mask_email(data.get('email'))} | Rol: {rol} | IP: {ip}",
            administrador=data.get("nombre") or "Sistema",
            origen=_role_origin(rol),
        )

    def _log_actor(self, actor, ip, modulo, accion, method, path):
        rol = actor.get("rol") if actor else ""
        registrar_log(
            modulo,
            accion,
            f"IP: {ip} | Rol: {rol or 'sistema'} | {method} {path}",
            administrador=actor.get("nombre") if actor else "Sistema",
            origen=_role_origin(rol),
        )
