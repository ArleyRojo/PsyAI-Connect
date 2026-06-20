import json
import time as _time

from flask import Blueprint, jsonify, request, session, Response

from app.services import admin_service, chatbot_config_events, chatbot_config_service, telemetry_service
from app.services.telemetry_service import _normalize_ip
from app.utils.auth import require_role
from app.utils.db import db_cursor
from app.repositories import admin_repository


def serialize_fecha(valor):
    if valor is None:
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


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


@admin_bp.route("/api/admin/usuarios-online", methods=["GET"])
@require_role("admin")
def get_usuarios_online():
    from app.services.telemetry_service import get_active_user_ids
    ids = get_active_user_ids()
    usuarios = admin_repository.get_users_by_ids(ids)
    return jsonify({"success": True, "usuarios": usuarios, "total": len(usuarios)}), 200


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
    
    try:
        with db_cursor(dictionary=True) as (_, cursor):
            cursor.execute("""
                SELECT nombre, idPaciente, mensajeUsuario, respuestaChatbot, nivelEmocionalDetectado, fecha
                FROM vistahistorialchatbot
                ORDER BY nombre ASC, fecha ASC
                LIMIT 200
            """)
            rows = cursor.fetchall()
            
            pacientes_map = {}
            for row in rows:
                paciente_key = row.get("idPaciente") or row["nombre"]
                if paciente_key not in pacientes_map:
                    pacientes_map[paciente_key] = {
                        "nombre": row["nombre"] or "Paciente",
                        "idPaciente": row.get("idPaciente"),
                        "total_mensajes": 0,
                        "ultimo_mensaje": None,
                        "nivel_max": "Bajo",
                        "mensajes": []
                    }
                p = pacientes_map[paciente_key]
                p["total_mensajes"] += 1
                
                rnivel = row.get("nivelEmocionalDetectado", "")
                if rnivel == "Alto":
                    p["nivel_max"] = "Alto"
                elif rnivel == "Medio" and p["nivel_max"] != "Alto":
                    p["nivel_max"] = "Medio"
                
                p["mensajes"].append({
                    "mensajeUsuario": row.get("mensajeUsuario"),
                    "respuestaChatbot": row.get("respuestaChatbot"),
                    "nivelEmocionalDetectado": rnivel,
                    "fecha": serialize_fecha(row.get("fecha"))
                })
                
                fecha = row.get("fecha")
                if fecha:
                    fecha_str = fecha.isoformat() if hasattr(fecha, 'isoformat') else str(fecha)
                    if p["ultimo_mensaje"] is None or fecha_str > p["ultimo_mensaje"]:
                        p["ultimo_mensaje"] = fecha_str
            
            pacientes = list(pacientes_map.values())
            
            if nivel:
                pacientes = [p for p in pacientes if p["nivel_max"] == nivel]
            if search:
                s = search.lower()
                pacientes = [p for p in pacientes if s in p["nombre"].lower()]
            
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
                "pacientes": pacientes,
                "stats": stats
            }), 200
    except Exception as e:
        estr = str(e)
        if "1146" in estr or "doesn't exist" in estr:
            return jsonify({
                "success": False,
                "message": "La vista vistahistorialchatbot no existe en la BD. "
                           "Corre las migraciones: python -m app.database.migrations",
                "pacientes": [],
                "stats": {"total": 0, "alto": 0, "medio": 0, "bajo": 0}
            }), 200
        return jsonify({"success": False, "message": estr}), 500
