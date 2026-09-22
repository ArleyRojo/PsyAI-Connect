import logging
from queue import Empty

from django.http import StreamingHttpResponse
from django.views import View
from rest_framework import viewsets, status
from rest_framework.response import Response

from apps.core.permissions import IsAuthenticatedDRF, IsPaciente
from apps.chatbot.serializers import (
    ChatbotEncuestaSerializer,
    ChatbotMensajeSerializer,
    ChatMensajeSerializer,
    ConsentimientoSerializer,
)
from apps.chatbot.services import (
    ChatEventsServiceManager,
    ChatbotConfigEventsService,
    ChatbotConfigService,
    ChatbotService,
    chatbot_config_events,
)

logger = logging.getLogger(__name__)

chatbot_service = ChatbotService()
chatbot_config_service = ChatbotConfigService()
mensajes_service = ChatEventsServiceManager()


class ChatbotViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def create(self, request):
        serializer = ChatbotMensajeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = chatbot_service.build_response(
            request.user_id,
            serializer.validated_data.get("mensaje"),
        )
        return Response(payload, status=status_code)

    def list(self, request):
        payload, status_code = chatbot_service.get_history(request.user_id)
        return Response(payload, status=status_code)

    def destroy(self, request):
        mensajes_service.eliminar_historial_chatbot(request.user_id)
        return Response({"success": True}, status=status.HTTP_200_OK)


class ChatbotEncuestaViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def create(self, request):
        serializer = ChatbotEncuestaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.chatbot.models import EncuestaChatbot

        try:
            encuesta = EncuestaChatbot.objects.create(
                idPaciente_id=request.user_id,
                utilidad=bool(data.get("utilidad")),
                claridad=bool(data.get("claridad")),
                recomendaria=data.get("recomendaria", "si"),
                comentario=data.get("comentario", ""),
            )
            return Response({"success": True, "id": encuesta.id}, status=status.HTTP_201_CREATED)
        except Exception:
            return Response({"success": False, "message": "Error al crear encuesta"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatbotConfigViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def list(self, request):
        config_data, _ = chatbot_config_service.get_config()
        cfg = config_data.get("config", {})
        daily_limit = int(cfg.get("daily_message_limit") or 20)
        used_today = chatbot_service.chat_repo.count_today_messages(request.user_id)
        return Response({
            "success": True,
            "config": {
                "max_tokens": cfg.get("max_tokens", 600),
                "max_tokens_user": cfg.get("max_tokens_user", 1000),
                "daily_message_limit": daily_limit,
                "crisis_phone": cfg.get("crisis_phone", "123"),
                "thinking_level": cfg.get("thinking_level", "medium"),
                "tone": cfg.get("tone", "empatico"),
            },
            "used": used_today,
            "limit": daily_limit,
        }, status=status.HTTP_200_OK)


class ChatbotConfigEventsResource(View):
    def get(self, request):
        queue = chatbot_config_events.subscribe()

        def stream():
            try:
                yield ": conectado\n\n"
                while True:
                    try:
                        event = queue.get(timeout=60)
                        yield f"event: chatbot-config\ndata: {event}\n\n"
                    except Empty:
                        yield ": keep-alive\n\n"
            finally:
                chatbot_config_events.unsubscribe(queue)

        response = StreamingHttpResponse(stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class ConsentimientoChatbotViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def list(self, request):
        try:
            from apps.patients.models import PerfilPaciente
            paciente = PerfilPaciente.objects.get(idPaciente_id=request.user_id)
            return Response({
                "success": True,
                "consentimiento_chatbot": getattr(paciente, "consentimiento_chatbot", False),
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response({
                "success": True,
                "consentimiento_chatbot": False,
            }, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = ConsentimientoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consent = bool(serializer.validated_data.get("consentimiento_chatbot"))
        try:
            from apps.patients.models import PerfilPaciente
            PerfilPaciente.objects.filter(idPaciente_id=request.user_id).update(
                consentimiento_chatbot=consent
            )
            return Response({"success": True, "consentimiento_chatbot": consent}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"success": False, "message": "Error al actualizar consentimiento"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatContactoViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def list(self, request):
        from apps.professionals.services import ProfessionalService
        professional_service = ProfessionalService()
        payload, _ = professional_service.list_professionals()
        profesionales = payload.get("profesionales", [])
        resultado = mensajes_service.get_contactos_con_mensajes(request.user_id, profesionales)
        return Response({"success": True, "profesionales": resultado}, status=status.HTTP_200_OK)


class ChatMensajeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def list(self, request):
        id_receptor = int(request.query_params.get("receptor") or 0)
        if not id_receptor:
            return Response({"success": False, "message": "Falta receptor"}, status=status.HTTP_400_BAD_REQUEST)
        msgs = mensajes_service.get_mensajes(
            request.user_id, id_receptor,
            int(request.query_params.get("desde", 0) or 0),
        )
        return Response({"success": True, "mensajes": msgs}, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = ChatMensajeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        receptor = data.get("receptor")
        mensaje = (data.get("mensaje") or "").strip()
        if not receptor or not mensaje:
            return Response({"success": False, "message": "Datos incompletos"}, status=status.HTTP_400_BAD_REQUEST)
        id_msg = mensajes_service.enviar_mensaje(request.user_id, receptor, mensaje)
        return Response({"success": True, "idMensaje": id_msg}, status=status.HTTP_201_CREATED)


class ChatHistorialDeleteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def destroy(self, request):
        mensajes_service.eliminar_historial_chatbot(request.user_id)
        return Response({"success": True}, status=status.HTTP_200_OK)