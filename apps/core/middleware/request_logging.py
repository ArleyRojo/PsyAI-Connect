import logging

logger = logging.getLogger("apps.core.request_logging")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            logger.info(
                "%s %s %s",
                request.method,
                request.path,
                response.status_code,
            )
        return response
