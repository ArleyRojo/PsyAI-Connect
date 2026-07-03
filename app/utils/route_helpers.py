from flask import jsonify, request, session

from app.utils.auth import AuthHelper


class RouteHelpers:
    @staticmethod
    def check_role(*roles):
        if "usuario" not in session:
            return jsonify({"success": False, "message": "No autenticado"}), 401
        if session.get("rol") not in roles:
            return jsonify({"success": False, "message": "No autorizado"}), 403
        return None

    @staticmethod
    def check_authenticated():
        return AuthHelper.require_authenticated()

    @staticmethod
    def check_admin():
        return AuthHelper.check_role("admin")

    @staticmethod
    def get_pagination():
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
