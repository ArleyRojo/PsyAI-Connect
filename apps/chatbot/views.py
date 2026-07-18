import json
import logging
from queue import Empty

from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.core.permissions import parse_json_body, require_auth, require_role

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


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotResource(View):
    def post(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        data, err = parse_json_body(request)
        if err:
            return err
        payload, status = chatbot_service.build_response(
            user["idUsuario"],
            data.get("mensaje"),
        )
        return JsonResponse(payload, status=status)

    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        payload, status = chatbot_service.get_history(user["idUsuario"])
        return JsonResponse(payload, status=status)

    def delete(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        mensajes_service.eliminar_historial_chatbot(user["idUsuario"])
        return JsonResponse({"success": True}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotEncuestaResource(View):
    def post(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        from apps.chatbot.models import EncuestaChatbot

        data, err = parse_json_body(request)
        if err:
            return err
        try:
            encuesta = EncuestaChatbot.objects.create(
                idPaciente_id=id_usuario,
                utilidad=bool(data.get("utilidad")),
                claridad=bool(data.get("claridad")),
                recomendaria=data.get("recomendaria", "si"),
                comentario=data.get("comentario", ""),
            )
            return JsonResponse({"success": True, "id": encuesta.id}, status=201)
        except Exception:
            return JsonResponse({"success": False, "message": "Error al crear encuesta"}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotConfigResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        config_data, _ = chatbot_config_service.get_config()
        return JsonResponse({
            "success": True,
            "config": {
                "max_tokens": config_data.get("config", {}).get("max_tokens", 600),
                "max_tokens_user": config_data.get("config", {}).get("max_tokens_user", 1000),
                "daily_message_limit": config_data.get("config", {}).get("daily_message_limit", 20),
            }
        }, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotConfigEventsResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            def error_stream():
                yield 'event: auth-error\ndata: {"message": "No autorizado"}\n\n'
            response = StreamingHttpResponse(error_stream(), content_type="text/event-stream")
            response.status_code = 200
            return response

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
        return response


@method_decorator(csrf_exempt, name="dispatch")
class ConsentimientoChatbotResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        try:
            from apps.patients.models import PerfilPaciente
            paciente = PerfilPaciente.objects.get(idPaciente_id=user["idUsuario"])
            return JsonResponse({
                "success": True,
                "consentimiento_chatbot": getattr(paciente, "consentimiento_chatbot", False),
            }, status=200)
        except Exception:
            return JsonResponse({
                "success": True,
                "consentimiento_chatbot": False,
            }, status=200)

    def post(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        data, err = parse_json_body(request)
        if err:
            return err
        consent = bool(data.get("consentimiento_chatbot"))
        try:
            from apps.patients.models import PerfilPaciente
            PerfilPaciente.objects.filter(idPaciente_id=user["idUsuario"]).update(
                consentimiento_chatbot=consent
            )
            return JsonResponse({"success": True, "consentimiento_chatbot": consent}, status=200)
        except Exception:
            return JsonResponse({"success": False, "message": "Error al actualizar consentimiento"}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class ChatContactoResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        from apps.professionals.services import ProfessionalService
        professional_service = ProfessionalService()
        payload, _ = professional_service.list_professionals()
        profesionales = payload.get("profesionales", [])
        resultado = mensajes_service.get_contactos_con_mensajes(user["idUsuario"], profesionales)
        return JsonResponse({"success": True, "profesionales": resultado}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class ChatMensajeResource(View):
    def get(self, request):
        user, err = require_auth(request)
        if err:
            return err

        id_receptor = int(request.GET.get("receptor") or 0)
        if not id_receptor:
            return JsonResponse({"success": False, "message": "Falta receptor"}, status=400)
        msgs = mensajes_service.get_mensajes(
            user["idUsuario"], id_receptor,
            int(request.GET.get("desde", 0) or 0),
        )
        return JsonResponse({"success": True, "mensajes": msgs}, status=200)

    def post(self, request):
        user, err = require_auth(request)
        if err:
            return err

        data, err = parse_json_body(request)
        if err:
            return err
        receptor = data.get("receptor")
        mensaje = (data.get("mensaje") or "").strip()
        if not receptor or not mensaje:
            return JsonResponse({"success": False, "message": "Datos incompletos"}, status=400)
        if len(mensaje) > 2000:
            return JsonResponse({"success": False, "message": "Mensaje demasiado largo"}, status=400)
        id_msg = mensajes_service.enviar_mensaje(user["idUsuario"], receptor, mensaje)
        return JsonResponse({"success": True, "idMensaje": id_msg}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ChatHistorialDeleteResource(View):
    def delete(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        mensajes_service.eliminar_historial_chatbot(user["idUsuario"])
        return JsonResponse({"success": True}, status=200)
