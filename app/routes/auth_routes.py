# ARCHIVO: auth_routes.py
# Autenticación: registro, inicio de sesión, cierre, verificación de sesión, recuperación de contraseña.
# Aplica rate limiting por endpoint (Flask-Limiter) y registra eventos de seguridad vía telemetría.
from flask import Blueprint, jsonify, request, session, current_app
from flask_limiter import RateLimitExceeded
from app.services import auth_service


auth_bp = Blueprint("auth", __name__)


# Consume un token del rate limiter configurado en app.config
def _consume_rate_limit(config_key):
    limiter = current_app.get_limiter()
    if not limiter:
        return
    with limiter.limit(current_app.config[config_key]):
        pass


@auth_bp.route("/api/register", methods=["POST"])
def register():
    try:
        _consume_rate_limit("REGISTER_RATE_LIMIT")
    except RateLimitExceeded:
        from app.services.telemetry_service import track_security_event
        track_security_event("actividad_sospechosa", f"Rate limit en registro desde {request.remote_addr}")
        return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
    payload, status = auth_service.register_user(request.get_json() or {})
    return jsonify(payload), status


@auth_bp.route("/api/login", methods=["POST"])
def login():
    try:
        _consume_rate_limit("LOGIN_RATE_LIMIT")
    except RateLimitExceeded:
        from app.services.telemetry_service import track_security_event
        track_security_event("actividad_sospechosa", f"Rate limit en login desde {request.remote_addr}")
        return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
    payload, status, session_user = auth_service.login_user(request.get_json() or {}, request.remote_addr)
    if not session_user:
        from app.services.telemetry_service import track_security_event
        track_security_event("fallos_login", f"IP: {request.remote_addr}")
    if session_user:
        session["usuario"] = session_user
        session["idUsuario"] = session_user["id"]
        session["nombre"] = session_user["nombre"]
        session["rol"] = session_user["rol"]
        session["fotoPerfil"] = session_user.get("fotoPerfil")
        session.permanent = True
        from flask import current_app
        current_app.logger.info(
            "Login exitoso: usuario=%s rol=%s id=%s",
            session_user.get("email"), session_user.get("rol"), session_user.get("id")
        )
    return jsonify(payload), status


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    uid = session.get("idUsuario")
    session.clear()
    if uid:
        from app.services.telemetry_service import remove_user
        remove_user(uid)
    return jsonify({"success": True, "message": "Sesion cerrada"}), 200


# Devuelve datos de sesión si el usuario está autenticado; verifica que la foto de perfil exista en disco
@auth_bp.route("/api/session", methods=["GET"])
def check_session():
    if session.get("idUsuario"):
        fp = session.get("fotoPerfil")
        if fp:
            import os
            fpath = os.path.join(current_app.root_path, "static", "uploads", fp)
            if not os.path.exists(fpath):
                session.pop("fotoPerfil", None)
                fp = None
        return jsonify(
            {
                "success": True,
                "logged_in": True,
                "usuario": {
                    "idUsuario": session.get("idUsuario"),
                    "id": session.get("idUsuario"),
                    "nombre": session.get("nombre"),
                    "rol": session.get("rol"),
                },
                "idUsuario": session.get("idUsuario"),
                "nombre": session.get("nombre"),
                "rol": session.get("rol"),
                "fotoPerfil": fp,
            }
        )
    return jsonify({"success": True, "logged_in": False})


@auth_bp.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    try:
        _consume_rate_limit("PASSWORD_RECOVERY_RATE_LIMIT")
    except RateLimitExceeded:
        return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429

    data = request.get_json() or {}
    email = data.get("email", "").strip()
    payload, status = auth_service.recover_password(email)
    return jsonify(payload), status


@auth_bp.route("/api/reset-password", methods=["POST"])
def reset_password():
    try:
        _consume_rate_limit("PASSWORD_RECOVERY_RATE_LIMIT")
    except RateLimitExceeded:
        return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429

    data = request.get_json() or {}
    payload, status = auth_service.reset_password(data)
    return jsonify(payload), status



