from functools import wraps
from flask import jsonify, session


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


def require_authenticated():
    if "usuario" not in session:
        return jsonify({"success": False, "message": "No autenticado"}), 401
    return None


def check_role(role):
    auth_error = require_authenticated()
    if auth_error:
        return auth_error
    if session.get("rol") != role:
        return jsonify({"success": False, "message": "No autorizado"}), 403
    return None