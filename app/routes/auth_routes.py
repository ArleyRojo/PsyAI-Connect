import os

from flask import Blueprint, jsonify, request, session, current_app
from flask.views import MethodView
from flask_limiter import RateLimitExceeded

from app.services.auth_service import AuthService
from app.services.telemetry_service import (
    track_security_event,
    remove_user as telemetry_remove_user,
)


auth_bp = Blueprint("auth", __name__)
auth_service = AuthService()


class AuthRouteHelpers:
    @staticmethod
    def consume_rate_limit(config_key):
        limiter = current_app.get_limiter()
        if not limiter:
            return
        with limiter.limit(current_app.config[config_key]):
            pass


class RegisterResource(MethodView):
    def post(self):
        try:
            AuthRouteHelpers.consume_rate_limit("REGISTER_RATE_LIMIT")
        except RateLimitExceeded:
            track_security_event("actividad_sospechosa", f"Rate limit en registro desde {request.remote_addr}")
            return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
        payload, status = auth_service.register_user(request.get_json() or {})
        return jsonify(payload), status


class LoginResource(MethodView):
    def post(self):
        try:
            AuthRouteHelpers.consume_rate_limit("LOGIN_RATE_LIMIT")
        except RateLimitExceeded:
            track_security_event("actividad_sospechosa", f"Rate limit en login desde {request.remote_addr}")
            return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
        payload, status, session_user = auth_service.login_user(request.get_json() or {}, request.remote_addr)
        if not session_user:
            track_security_event("fallos_login", f"IP: {request.remote_addr}")
        if session_user:
            session["usuario"] = session_user
            session["idUsuario"] = session_user["id"]
            session["nombre"] = session_user["nombre"]
            session["rol"] = session_user["rol"]
            session["fotoPerfil"] = session_user.get("fotoPerfil")
            session.permanent = True
            current_app.logger.info(
                "Login exitoso: usuario=%s rol=%s id=%s",
                session_user.get("email"), session_user.get("rol"), session_user.get("id"),
            )
        return jsonify(payload), status


class LogoutResource(MethodView):
    def post(self):
        uid = session.get("idUsuario")
        session.clear()
        if uid:
            telemetry_remove_user(uid)
        return jsonify({"success": True, "message": "Sesion cerrada"}), 200


class SessionResource(MethodView):
    def get(self):
        if session.get("idUsuario"):
            fp = session.get("fotoPerfil")
            if fp:
                fpath = os.path.join(current_app.root_path, "static", "uploads", fp)
                if not os.path.exists(fpath):
                    session.pop("fotoPerfil", None)
                    fp = None
            return jsonify({
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
            })
        return jsonify({"success": True, "logged_in": False})


class ForgotPasswordResource(MethodView):
    def post(self):
        try:
            AuthRouteHelpers.consume_rate_limit("PASSWORD_RECOVERY_RATE_LIMIT")
        except RateLimitExceeded:
            return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
        data = request.get_json() or {}
        email = data.get("email", "").strip()
        payload, status = auth_service.recover_password(email)
        return jsonify(payload), status


class ResetPasswordResource(MethodView):
    def post(self):
        try:
            AuthRouteHelpers.consume_rate_limit("PASSWORD_RECOVERY_RATE_LIMIT")
        except RateLimitExceeded:
            return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429
        data = request.get_json() or {}
        payload, status = auth_service.reset_password(data)
        return jsonify(payload), status


auth_bp.add_url_rule("/api/register", view_func=RegisterResource.as_view("register"))
auth_bp.add_url_rule("/api/login", view_func=LoginResource.as_view("login"))
auth_bp.add_url_rule("/api/logout", view_func=LogoutResource.as_view("logout"))
auth_bp.add_url_rule("/api/session", view_func=SessionResource.as_view("session"))
auth_bp.add_url_rule("/api/forgot-password", view_func=ForgotPasswordResource.as_view("forgot_password"))
auth_bp.add_url_rule("/api/reset-password", view_func=ResetPasswordResource.as_view("reset_password"))
