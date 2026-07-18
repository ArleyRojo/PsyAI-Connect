import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data.get("detail", response.data) if isinstance(response.data, dict) else response.data
        if isinstance(detail, list) and len(detail) == 1:
            detail = detail[0]
        response.data = {
            "success": False,
            "message": str(detail) if detail else "Error del servidor",
            "code": response.status_code,
        }
    else:
        logger.exception("Unhandled exception: %s", exc)

    return response
