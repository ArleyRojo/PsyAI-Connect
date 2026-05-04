from flask import Blueprint, jsonify, request, session, current_app
from flask_limiter import RateLimitExceeded
from app.services import auth_service


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/register", methods=["POST"])
def register():
    limiter = current_app.get_limiter()
    try:
        with limiter.limit("5 per minute"):
            pass
    except RateLimitExceeded:
        return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
    payload, status = auth_service.register_user(request.get_json() or {})
    return jsonify(payload), status


@auth_bp.route("/api/login", methods=["POST"])
def login():
    limiter = current_app.get_limiter()
    try:
        with limiter.limit("10 per minute"):
            pass
    except RateLimitExceeded:
        return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
    payload, status, session_user = auth_service.login_user(request.get_json() or {}, request.remote_addr)
    if session_user:
        session["usuario"] = session_user
        session["idUsuario"] = session_user["id"]
        session["nombre"] = session_user["nombre"]
        session["rol"] = session_user["rol"]
        session["fotoPerfil"] = session_user.get("fotoPerfil")
        session.permanent = True
    return jsonify(payload), status


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Sesion cerrada"}), 200


@auth_bp.route("/api/session", methods=["GET"])
def check_session():
    if session.get("idUsuario"):
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
                "fotoPerfil": session.get("fotoPerfil"),
            }
        )
    return jsonify({"success": True, "logged_in": False})


@auth_bp.route("/api/recover", methods=["POST"])
def recover_password():
    limiter = current_app.get_limiter()
    try:
        with limiter.limit("3 per minute"):
            pass
    except RateLimitExceeded:
        return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
    payload, status = auth_service.recover_password(request.get_json() or {})
    return jsonify(payload), status


@auth_bp.route("/api/reset-password", methods=["POST"])
def reset_password():
    limiter = current_app.get_limiter()
    try:
        with limiter.limit("3 per minute"):
            pass
    except RateLimitExceeded:
        return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
    payload, status = auth_service.reset_password(request.get_json() or {})
    return jsonify(payload), status
