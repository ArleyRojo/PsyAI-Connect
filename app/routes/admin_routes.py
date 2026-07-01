# ARCHIVO: admin_routes.py
# Rutas del panel de administración: estadísticas, usuarios, roles, logs, chatbot.
# Todas requieren rol "admin". Usa SSE para streaming de stats y logs en tiempo real.
import json
import time as _time

from flask import Blueprint, jsonify, request, session, Response

from app.services import admin_service, chatbot_config_events, chatbot_config_service, telemetry_service
from app.services.telemetry_service import _normalize_ip
from app.utils.auth import require_role
from app.repositories import admin_repository


admin_bp = Blueprint("admin", __name__)


# Helper: extrae paginación de query params con valores por defecto seguros
def _get_pagination():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    return page, limit


@admin_bp.route("/api/admin/crear-columnas-diagnostico", methods=["POST"])
@require_role("admin")
def crear_columnas_diagnostico():
    payload, status = admin_service.create_report_columns()
    return jsonify(payload), status


@admin_bp.route("/api/admin/stats", methods=["GET"])
@require_role("admin")
def get_admin_stats():
    payload, status = admin_service.get_stats()
    return jsonify(payload), status


# SSE en vivo: notifica al panel admin cuando cambian las estadísticas
@admin_bp.route("/api/admin/stats/stream")
@require_role("admin")
def stats_stream():
    client_ip = _normalize_ip(request.remote_addr or '127.0.0.1')
    telemetry_service.sse_connected(client_ip)

    def generate():
        last_version = -1
        last_emit = 0
        poll_count = 0
        try:
            while True:
                telemetry_service.sse_heartbeat(client_ip)
                current_version = telemetry_service._version
                now = _time.time()
                force = current_version != last_version
                timed = now - last_emit >= 5
                if force or timed:
                    last_version = current_version
                    last_emit = now
                    payload, _ = admin_service.get_stats(force=force)
                    yield f"data: {json.dumps(payload)}\n\n"
                    poll_count = 0
                else:
                    poll_count += 1
                    if poll_count >= 4:
                        yield ": heartbeat\n\n"
                _time.sleep(1)
        finally:
            telemetry_service.sse_disconnected(client_ip)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# SSE en vivo: transmite los últimos logs cuando cambia su versión
@admin_bp.route("/api/admin/logs/stream")
@require_role("admin")
def logs_stream():
    def generate():
        last_version = -1
        while True:
            current_version = admin_repository.get_logs_version()
            if current_version != last_version:
                last_version = current_version
                logs = admin_repository.get_logs(limit=10)
                logs.sort(key=lambda x: x["fecha"], reverse=True)
                yield f"data: {json.dumps({'success': True, 'logs': logs})}\n\n"
            _time.sleep(0.5)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# CRUD de usuarios desde el panel admin
@admin_bp.route("/api/admin/usuarios", methods=["GET"])
@require_role("admin")
def get_usuarios():
    page, limit = _get_pagination()
    payload, status = admin_service.list_users(page, limit)
    return jsonify(payload), status


@admin_bp.route("/api/admin/usuarios/<int:id_usuario>", methods=["GET"])
@require_role("admin")
def get_usuario(id_usuario: int):
    payload, status = admin_service.get_user(id_usuario)
    return jsonify(payload), status


@admin_bp.route("/api/admin/usuarios", methods=["POST"])
@require_role("admin")
def crear_usuario():
    payload, status = admin_service.create_user(request.get_json() or {})
    return jsonify(payload), status


@admin_bp.route("/api/admin/usuarios/<int:id_usuario>", methods=["PUT"])
@require_role("admin")
def editar_usuario(id_usuario: int):
    data = request.get_json() or {}
    data["idUsuario"] = id_usuario
    payload, status = admin_service.update_user(data)
    return jsonify(payload), status


@admin_bp.route("/api/admin/usuarios/<int:id_usuario>", methods=["DELETE"])
@require_role("admin")
def eliminar_usuario(id_usuario: int):
    payload, status = admin_service.delete_user(id_usuario)
    return jsonify(payload), status


@admin_bp.route("/api/admin/usuarios/<int:id_usuario>/bloquear", methods=["PATCH"])
@require_role("admin")
def bloquear_usuario(id_usuario: int):
    data = request.get_json() or {}
    data["idUsuario"] = id_usuario
    payload, status = admin_service.block_user(data)
    return jsonify(payload), status


# Gestión de roles: listar usuarios por rol, cambiar rol, historial de cambios
@admin_bp.route("/api/admin/roles/usuarios", methods=["GET"])
@require_role("admin")
def get_usuarios_roles():
    payload, status = admin_service.list_role_users()
    return jsonify(payload), status


@admin_bp.route("/api/admin/usuarios/<int:id_usuario>/rol", methods=["PATCH"])
@require_role("admin")
def cambiar_rol(id_usuario: int):
    data = request.get_json() or {}
    data["idUsuario"] = id_usuario
    payload, status = admin_service.change_role(data)
    return jsonify(payload), status


@admin_bp.route("/api/admin/roles/historial", methods=["GET"])
@require_role("admin")
def get_historial_roles():
    payload, status = admin_service.role_history()
    return jsonify(payload), status


# Notificaciones del sistema (crear, listar, eliminar)
@admin_bp.route("/api/admin/notificaciones", methods=["GET"])
@require_role("admin")
def get_notificaciones():
    payload, status = admin_service.notifications_feed()
    return jsonify(payload), status


@admin_bp.route("/api/admin/notificaciones", methods=["POST"])
@require_role("admin")
def crear_notificacion():
    payload, status = admin_service.create_notification(request.get_json() or {})
    return jsonify(payload), status


@admin_bp.route("/api/admin/notificaciones/<int:id_notificacion>", methods=["DELETE"])
@require_role("admin")
def eliminar_notificacion(id_notificacion: int):
    payload, status = admin_service.delete_notification(id_notificacion)
    return jsonify(payload), status


# Logs de auditoría y usuarios online
@admin_bp.route("/api/admin/logs", methods=["GET"])
@require_role("admin")
def get_logs():
    payload, status = admin_service.get_logs()
    return jsonify(payload), status


@admin_bp.route("/api/admin/usuarios-online", methods=["GET"])
@require_role("admin")
def get_usuarios_online():
    from app.services.telemetry_service import get_active_user_ids
    ids = get_active_user_ids()
    usuarios = admin_repository.get_users_by_ids(ids)
    return jsonify({"success": True, "usuarios": usuarios, "total": len(usuarios)}), 200


# Configuración del chatbot (leer, actualizar, términos de riesgo, palabras detectadas, historial)
@admin_bp.route("/api/admin/chatbot-config", methods=["GET"])
@require_role("admin")
def get_chatbot_config():
    payload, status = chatbot_config_service.get_config(), 200
    return jsonify({"success": True, "config": payload}), status


@admin_bp.route("/api/admin/chatbot-config", methods=["PUT"])
@require_role("admin")
def update_chatbot_config():
    data = request.get_json() or {}
    admin_id = session.get("idUsuario")
    payload, status = chatbot_config_service.save_config(data, admin_id)
    if status < 400 and payload.get("success"):
        # Publica evento SSE para que los pacientes reciban la nueva config en vivo
        chatbot_config_events.publish_config_update({
            "max_tokens": data.get("max_tokens"),
            "max_tokens_user": data.get("max_tokens_user"),
            "daily_message_limit": data.get("daily_message_limit"),
        })
    return jsonify(payload), status


@admin_bp.route("/api/admin/chatbot-config/clear-risk-terms", methods=["DELETE"])
@require_role("admin")
def clear_chatbot_risk_terms():
    admin_id = session.get("idUsuario")
    body, status = chatbot_config_service.clear_risk_terms(admin_id)
    return jsonify(body), status


@admin_bp.route("/api/admin/chatbot-risk-terms", methods=["PUT"])
@require_role("admin")
def save_chatbot_risk_terms():
    admin_id = session.get("idUsuario")
    data = request.get_json(silent=True) or {}
    risk_terms_str = data.get("risk_terms", "[]")
    body, status = chatbot_config_service.save_risk_terms_only(risk_terms_str, admin_id)
    return jsonify(body), status


@admin_bp.route("/api/admin/chatbot-detected-words", methods=["GET"])
@require_role("admin")
def get_chatbot_detected_words():
    palabras = chatbot_config_service.get_detected_risk_words()
    return jsonify({"success": True, "palabras": palabras}), 200


@admin_bp.route("/api/admin/chatbot-historial", methods=["GET"])
@require_role("admin")
def get_chatbot_historial():
    nivel = request.args.get("nivel", "")
    search = request.args.get("q", "")
    payload, status = admin_service.get_chatbot_historial(nivel, search)
    return jsonify(payload), status
