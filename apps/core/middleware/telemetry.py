import time
import logging

from django.utils.deprecation import MiddlewareMixin

from apps.admin_panel.services import (
    telemetry_service,
    track_request,
    track_latency,
    _normalize_ip,
)

logger = logging.getLogger(__name__)

# Paths to ignore for telemetry tracking
IGNORED_PATHS = (
    "/static/",
    "/uploads/",
    "/favicon.ico",
    "/healthz",
    "/api/admin/stats/stream",
    "/api/admin/logs/stream",
)


class TelemetryMiddleware(MiddlewareMixin):
    """
    Middleware to track request telemetry for the admin dashboard real-time charts.
    Tracks requests, latency, and feeds data to TelemetryService.
    """

    def process_request(self, request):
        # Store start time for latency calculation
        request._telemetry_start_time = time.perf_counter()
        return None

    def process_response(self, request, response):
        # Calculate latency
        start_time = getattr(request, "_telemetry_start_time", None)
        if start_time is not None:
            duration_ms = (time.perf_counter() - start_time) * 1000
        else:
            duration_ms = 0

        # Get request path and IP
        path = request.path
        ip = _normalize_ip(request.META.get("REMOTE_ADDR", "127.0.0.1"))
        user_id = getattr(request, "user_id", None) or request.session.get("idUsuario")

        # Skip ignored paths
        if any(path.startswith(p) for p in IGNORED_PATHS):
            return response

        # Track request and latency in telemetry service (wrapped in try/except)
        try:
            track_request(ip, path, user_id)
            track_latency(duration_ms)
        except Exception:
            # Never break the response due to telemetry errors
            logger.exception("Telemetry tracking failed for %s %s", request.method, path)

        return response