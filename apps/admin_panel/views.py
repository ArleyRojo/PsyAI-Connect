import json
import time as _time

from django.http import StreamingHttpResponse
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_panel.services import (
    AdminService,
    telemetry_service,
    _normalize_ip,
    get_active_user_ids,
)
from apps.core.permissions import IsAuthenticatedDRF, IsAdmin
from apps.admin_panel.repositories import AdminRepository

admin_service = AdminService()
admin_repo = AdminRepository()


class AdminDiagnosticoAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def post(self, request):
        payload, status_code = admin_service.create_report_columns()
        return Response(payload, status=status_code)


class AdminStatsAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def get(self, request):
        payload, status_code = admin_service.get_stats()
        return Response(payload, status=status_code)


class AdminStatsStreamAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def get(self, request):
        client_ip = _normalize_ip(request.META.get("REMOTE_ADDR", "127.0.0.1"))
        telemetry_service.sse_connected(client_ip)

        def generate():
            last_version = -1
            last_emit = 0
            poll_count = 0
            try:
                while True:
                    telemetry_service.sse_heartbeat(client_ip)
                    current_version = telemetry_service._version
                    now = _time.time()
                    force = current_version != last_version
                    timed = now - last_emit >= 5
                    if force or timed:
                        last_version = current_version
                        last_emit = now
                        payload, _ = admin_service.get_stats(force=force)
                        yield f"data: {json.dumps(payload)}\n\n"
                        poll_count = 0
                    else:
                        poll_count += 1
                        if poll_count >= 4:
                            yield ": heartbeat\n\n"
                    _time.sleep(1)
            finally:
                telemetry_service.sse_disconnected(client_ip)

        response = StreamingHttpResponse(
            generate(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AdminLogsStreamAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def get(self, request):
        client_ip = _normalize_ip(request.META.get("REMOTE_ADDR", "127.0.0.1"))
        telemetry_service.sse_connected(client_ip)

        def generate():
            last_version = -1
            last_emit = 0
            poll_count = 0
            try:
                while True:
                    telemetry_service.sse_heartbeat(client_ip)
                    current_version = AdminRepository.get_logs_version()
                    now = _time.time()
                    force = current_version != last_version
                    timed = now - last_emit >= 3
                    if force or timed:
                        last_version = current_version
                        last_emit = now
                        logs = admin_repo.get_logs(limit=10)
                        logs.sort(key=lambda x: x.get("fecha", ""), reverse=True)
                        yield f"data: {json.dumps({'success': True, 'logs': logs})}\n\n"
                        poll_count = 0
                    else:
                        poll_count += 1
                        if poll_count >= 4:
                            yield ": heartbeat\n\n"
                    _time.sleep(1)
            finally:
                telemetry_service.sse_disconnected(client_ip)

        response = StreamingHttpResponse(
            generate(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AdminUsuarioViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def list(self, request):
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))
        payload, status_code = admin_service.list_users(page, limit)
        return Response(payload, status=status_code)

    def retrieve(self, request, pk=None):
        payload, status_code = admin_service.get_user(int(pk))
        return Response(payload, status=status_code)

    def create(self, request):
        data = request.data.copy() if request.data else {}
        payload, status_code = admin_service.create_user(data)
        return Response(payload, status=status_code)

    def update(self, request, pk=None):
        data = request.data.copy() if request.data else {}
        data["idUsuario"] = int(pk)
        payload, status_code = admin_service.update_user(data)
        return Response(payload, status=status_code)

    def partial_update(self, request, pk=None):
        data = request.data.copy() if request.data else {}

        accion = data.get("accion")
        if accion:
            if accion not in ("bloquear", "suspender", "reestablecer", "desbloquear"):
                return Response(
                    {"success": False, "message": f"Acción inválida: {accion}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data["idUsuario"] = int(pk)
            payload, status_code = admin_service.block_user(data)
        elif data.get("nuevoRol"):
            data["idUsuario"] = int(pk)
            payload, status_code = admin_service.change_role(data)
        else:
            return Response(
                {"success": False, "message": "Acción no especificada (accion o nuevoRol)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(payload, status=status_code)

    def destroy(self, request, pk=None):
        payload, status_code = admin_service.delete_user(int(pk))
        return Response(payload, status=status_code)


class AdminRolAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def get(self, request):
        filter_param = request.query_params.get("filter", "")
        if filter_param == "historial":
            payload, status_code = admin_service.role_history()
        else:
            payload, status_code = admin_service.list_role_users()
        return Response(payload, status=status_code)


class AdminNotificacionAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def get(self, request):
        payload, status_code = admin_service.notifications_feed()
        return Response(payload, status=status_code)

    def post(self, request):
        data = request.data.copy() if request.data else {}
        payload, status_code = admin_service.create_notification(data)
        return Response(payload, status=status_code)

    def delete(self, request, id_notificacion=None):
        if not id_notificacion:
            return Response(
                {"success": False, "message": "Falta id de notificación"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload, status_code = admin_service.delete_notification(id_notificacion)
        return Response(payload, status=status_code)


class AdminLogAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def get(self, request):
        payload, status_code = admin_service.get_logs()
        return Response(payload, status=status_code)


class AdminOnlineAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def get(self, request):
        ids = get_active_user_ids()
        usuarios = admin_repo.get_users_by_ids(ids)
        return Response({"success": True, "usuarios": usuarios, "total": len(usuarios)}, status=200)


class AdminChatbotHistorialAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def get(self, request):
        nivel = request.query_params.get("nivel", "")
        search = request.query_params.get("q", "")
        payload, status_code = admin_service.get_chatbot_historial(nivel, search)
        return Response(payload, status=status_code)


class AdminChatbotConfigViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def list(self, request):
        from apps.chatbot.services import ChatbotConfigService
        chatbot_config_service = ChatbotConfigService()
        payload, status_code = chatbot_config_service.get_config()
        return Response(payload, status=status_code)

    def create(self, request):
        from apps.chatbot.services import ChatbotConfigService, ChatbotConfigEventsService
        chatbot_config_service = ChatbotConfigService()
        chatbot_config_events = ChatbotConfigEventsService()
        data = request.data.copy() if request.data else {}
        admin_id = getattr(request, "user_id", None)
        payload, status_code = chatbot_config_service.save_config(data, admin_id)
        if status_code < 400 and payload.get("success"):
            chatbot_config_events.publish_config_update({
                "max_tokens": data.get("max_tokens"),
                "max_tokens_user": data.get("max_tokens_user"),
                "daily_message_limit": data.get("daily_message_limit"),
            })
        return Response(payload, status=status_code)

    def update(self, request, pk=None):
        from apps.chatbot.services import ChatbotConfigService, ChatbotConfigEventsService
        chatbot_config_service = ChatbotConfigService()
        chatbot_config_events = ChatbotConfigEventsService()
        data = request.data.copy() if request.data else {}
        admin_id = getattr(request, "user_id", None)
        payload, status_code = chatbot_config_service.save_config(data, admin_id)
        if status_code < 400 and payload.get("success"):
            chatbot_config_events.publish_config_update({
                "max_tokens": data.get("max_tokens"),
                "max_tokens_user": data.get("max_tokens_user"),
                "daily_message_limit": data.get("daily_message_limit"),
            })
        return Response(payload, status=status_code)

    def partial_update(self, request, pk=None):
        from apps.chatbot.services import ChatbotConfigService
        chatbot_config_service = ChatbotConfigService()
        admin_id = getattr(request, "user_id", None)
        data = request.data.copy() if request.data else {}
        risk_terms_str = data.get("risk_terms")
        if risk_terms_str is not None:
            body, status_code = chatbot_config_service.save_risk_terms(risk_terms_str, admin_id)
            return Response(body, status=status_code)
        return Response(
            {"success": False, "message": "Falta risk_terms en el body"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, pk=None):
        from apps.chatbot.services import ChatbotConfigService
        chatbot_config_service = ChatbotConfigService()
        admin_id = getattr(request, "user_id", None)
        body, status_code = chatbot_config_service.clear_risk_terms(admin_id)
        return Response(body, status=status_code)


class AdminChatbotPalabrasAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsAdmin]

    def get(self, request):
        from apps.chatbot.services import ChatbotConfigService
        chatbot_config_service = ChatbotConfigService()
        payload, status_code = chatbot_config_service.get_historial_palabras_riesgo()
        return Response(payload, status=status_code)
