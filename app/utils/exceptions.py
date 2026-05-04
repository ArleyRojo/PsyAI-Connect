import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 400, payload: dict = None):
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}
        super().__init__(message)

    def to_dict(self):
        rv = dict(self.payload)
        rv["success"] = False
        rv["message"] = self.message
        return rv


class BadRequestError(APIError):
    def __init__(self, message: str, payload: dict = None):
        super().__init__(message, 400, payload)


class UnauthorizedError(APIError):
    def __init__(self, message: str = "No autenticado", payload: dict = None):
        super().__init__(message, 401, payload)


class ForbiddenError(APIError):
    def __init__(self, message: str = "No autorizado", payload: dict = None):
        super().__init__(message, 403, payload)


class NotFoundError(APIError):
    def __init__(self, message: str = "Recurso no encontrado", payload: dict = None):
        super().__init__(message, 404, payload)


class ConflictError(APIError):
    def __init__(self, message: str, payload: dict = None):
        super().__init__(message, 409, payload)


class RateLimitError(APIError):
    def __init__(self, message: str = "Demasiadas solicitudes", payload: dict = None):
        super().__init__(message, 429, payload)


def handle_exception(e):
    if isinstance(e, APIError):
        return jsonify(e.to_dict()), e.status_code

    if isinstance(e, HTTPException):
        return jsonify({
            "success": False,
            "message": e.description or "Error HTTP"
        }), e.code

    logger.exception(f"Unhandled exception: {e}")
    return jsonify({
        "success": False,
        "message": "Error interno del servidor"
    }), 500


def success_response(data: dict, message: str = None, status_code: int = 200):
    response = {"success": True}
    if message:
        response["message"] = message
    response.update(data)
    return jsonify(response), status_code


def error_response(message: str, status_code: int = 400, **kwargs):
    response = {"success": False, "message": message}
    response.update(kwargs)
    return jsonify(response), status_code