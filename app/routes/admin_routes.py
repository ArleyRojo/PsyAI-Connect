from flask import Blueprint, jsonify, request, session

from app.services import admin_service, chatbot_config_events, chatbot_config_service
from app.utils.auth import require_role
from app.utils.db import db_cursor


admin_bp = Blueprint("admin", __name__)


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


@admin_bp.route("/api/admin/logs", methods=["GET"])
@require_role("admin")
def get_logs():
    payload, status = admin_service.get_logs()
    return jsonify(payload), status


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
        chatbot_config_events.publish_config_update({
            "max_tokens": data.get("max_tokens"),
        })
    return jsonify(payload), status


@admin_bp.route("/api/admin/chatbot-config/clear-risk-terms", methods=["DELETE"])
@require_role("admin")
def clear_chatbot_risk_terms():
    admin_id = session.get("idUsuario")
    result = chatbot_config_service.clear_risk_terms(admin_id)
    return jsonify(result), 200


@admin_bp.route("/api/admin/chatbot-historial", methods=["GET"])
@require_role("admin")
def get_chatbot_historial():
    nivel = request.args.get("nivel", "")
    
    try:
        with db_cursor(dictionary=True) as (_, cursor):
            if nivel:
                cursor.execute(
                    """
                    SELECT nombre, mensajeUsuario, respuestaChatbot, nivelEmocionalDetectado, fecha
                    FROM vistahistorialchatbot
                    WHERE nivelEmocionalDetectado = %s
                    ORDER BY fecha DESC
                    LIMIT 200
                    """,
                    (nivel,)
                )
            else:
                cursor.execute(
                    """
                    SELECT nombre, mensajeUsuario, respuestaChatbot, nivelEmocionalDetectado, fecha
                    FROM vistahistorialchatbot
                    ORDER BY fecha DESC
                    LIMIT 200
                    """
                )
            historial = cursor.fetchall()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN nivelEmocionalDetectado = 'Alto' THEN 1 ELSE 0 END) as alto,
                    SUM(CASE WHEN nivelEmocionalDetectado = 'Medio' THEN 1 ELSE 0 END) as medio,
                    SUM(CASE WHEN nivelEmocionalDetectado = 'Bajo' THEN 1 ELSE 0 END) as bajo
                FROM vistahistorialchatbot
            """)
            stats = cursor.fetchone()
            
            return jsonify({
                "success": True,
                "historial": historial,
                "stats": stats
            }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
