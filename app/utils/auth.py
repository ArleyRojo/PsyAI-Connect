from functools import wraps
from flask import jsonify, session


class AuthHelper:
    @staticmethod
    def require_role(*roles):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if "usuario" not in session:
                    return jsonify({"success": False, "message": "No autenticado"}), 401
                user_role = session.get("rol")
                if user_role not in roles:
                    return jsonify({"success": False, "message": "No autorizado"}), 403
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    @staticmethod
    def require_authenticated():
        if "usuario" not in session:
            return jsonify({"success": False, "message": "No autenticado"}), 401
        return None

    @staticmethod
    def check_role(role):
        auth_error = AuthHelper.require_authenticated()
        if auth_error:
            return auth_error
        if session.get("rol") != role:
            return jsonify({"success": False, "message": "No autorizado"}), 403
        return None
