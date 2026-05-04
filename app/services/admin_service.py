import secrets
from app.repositories import admin_repository


def init_db():
    try:
        admin_repository.ensure_report_columns()
    except Exception as exc:
        from flask import current_app
        current_app.logger.error(f"Error initializing DB: {exc}")


def create_report_columns():
    admin_repository.ensure_report_columns()
    return {"success": True, "message": "Columnas creadas correctamente"}, 200


def get_stats():
    return {"success": True, "stats": admin_repository.get_stats()}, 200


def list_users(page=1, limit=20):
    return {"success": True, "usuarios": admin_repository.list_users(page, limit)}, 200


def get_user(user_id):
    usuario = admin_repository.get_user(user_id)
    if not usuario:
        return {"success": False, "message": "Usuario no encontrado"}, 404
    return {"success": True, "usuario": usuario}, 200


def create_user(data):
    if not data.get("contrasena"):
        temp_password = secrets.token_urlsafe(10)
        data["contrasena"] = temp_password
        admin_repository.create_user(data)
        return {"success": True, "message": "Usuario creado correctamente", "contrasena_temporal": temp_password}, 200
    admin_repository.create_user(data)
    return {"success": True, "message": "Usuario creado correctamente"}, 200


def update_user(data):
    admin_repository.update_user(data)
    return {"success": True, "message": "Usuario actualizado"}, 200


def delete_user(user_id):
    admin_repository.delete_user(user_id)
    return {"success": True, "message": "Usuario eliminado"}, 200


def block_user(data):
    activo = admin_repository.block_user(data.get("idUsuario"), data.get("accion"))
    return {"success": True, "message": f"Usuario {'suspendido' if activo == 0 else 'reestablecido'}"}, 200


def list_role_users():
    return {"success": True, "usuarios": admin_repository.list_role_users()}, 200


def change_role(data):
    admin_repository.change_role(data.get("idUsuario"), data.get("nuevoRol"))
    return {"success": True, "message": "Rol actualizado"}, 200


def role_history():
    historial = admin_repository.get_role_history()
    for item in historial:
        if item.get("fecha"):
            item["fecha"] = item["fecha"].strftime("%d/%m/%Y %H:%M")
    return {"success": True, "historial": historial}, 200


def notifications_feed():
    actividades = admin_repository.get_notifications_feed()
    actividades.sort(key=lambda x: x["fecha"], reverse=True)
    stats = _notification_stats(actividades)
    return {
        "success": True,
        "notificaciones": actividades[:100],
        "stats": stats,
    }, 200


def _notification_stats(actividades):
    total = len(actividades)
    enviadas = sum(1 for item in actividades if item.get("estado") != "pendiente")
    programadas = sum(1 for item in actividades if item.get("estado") == "pendiente")
    alcanzados = sum(
        1 for item in actividades
        if item.get("estado") != "pendiente"
        and (item.get("destinatario") or item.get("email_individual") or item.get("mensaje"))
    )
    return {
        "enviadas": enviadas,
        "programadas": programadas,
        "tasa": f"{round((enviadas / total) * 100)}%" if total else "0%",
        "alcanzados": alcanzados,
    }


def create_notification(data):
    admin_repository.create_notification(data)
    return {"success": True, "message": "Notificacion enviada"}, 200


def delete_notification(notification_id):
    admin_repository.delete_notification(notification_id)
    return {"success": True, "message": "Notificacion eliminada"}, 200


def get_logs():
    logs = admin_repository.get_logs()
    logs.sort(key=lambda x: x["fecha"], reverse=True)
    return {"success": True, "logs": logs}, 200
