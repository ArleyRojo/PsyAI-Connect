import os

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.core.permissions import parse_json_body, require_auth, require_role
from apps.patients.services import PatientService

try:
    from apps.chatbot.services import ChatbotService
except ImportError:
    ChatbotService = None

try:
    from apps.chatbot.services import ChatEventsServiceManager as MensajesService
except ImportError:
    MensajesService = None

try:
    from apps.chatbot.services import ChatbotConfigService, chatbot_config_events
except ImportError:
    ChatbotConfigService = None
    chatbot_config_events = None

try:
    from apps.documents.services import DocumentoService
except ImportError:
    DocumentoService = None


def _get_patient_service():
    return PatientService()


@method_decorator(csrf_exempt, name="dispatch")
class PerfilPacienteResource(View):
    def get(self, request, id_usuario=None):
        user, err = require_auth(request)
        if err:
            return err
        if user["rol"] not in ("admin", "profesional") and int(user["idUsuario"]) != id_usuario:
            return JsonResponse({"success": False, "message": "No autorizado"}, status=403)
        payload, status = _get_patient_service().get_patient_profile(id_usuario)
        return JsonResponse(payload, status=status)

    def put(self, request, id_usuario=None):
        user, err = require_auth(request)
        if err:
            return err
        if user["rol"] != "paciente":
            return JsonResponse({"success": False, "message": "No autorizado"}, status=403)
        data, err = parse_json_body(request)
        if err:
            return err
        data["idUsuario"] = user["idUsuario"]
        payload, status = _get_patient_service().update_patient_profile(data)
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class PerfilFotoResource(View):
    def _handle(self, request):
        user, err = require_auth(request)
        if err:
            return err
        file = request.FILES.get("foto") or request.FILES.get("fotoPerfil")
        payload, status = _get_patient_service().update_profile_photo(user["idUsuario"], file)
        return JsonResponse(payload, status=status)

    def put(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)


@method_decorator(csrf_exempt, name="dispatch")
class EvolucionResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        payload, status = _get_patient_service().get_evolution_history(user["idUsuario"])
        return JsonResponse(payload, status=status)

    def post(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        payload, status = _get_patient_service().save_evolution(user["idUsuario"], parse_json_body(request)[0] or {})
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class PacienteResource(View):
    def get(self, request):
        user, err = require_role(request, "profesional", "admin")
        if err:
            return err
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        payload, status = _get_patient_service().list_patients(page, limit)
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class ProfesionalResource(View):
    def get(self, request):
        user, err = require_auth(request)
        if err:
            return err
        payload, status = _get_patient_service().list_professionals()
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotResource(View):
    def post(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        if not ChatbotService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        data, err = parse_json_body(request)
        if err:
            return err
        svc = ChatbotService()
        payload, status = svc.build_response(user["idUsuario"], data.get("mensaje"))
        return JsonResponse(payload, status=status)

    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        if not ChatbotService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = ChatbotService()
        payload, status = svc.get_history(user["idUsuario"])
        return JsonResponse(payload, status=status)

    def delete(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        if not MensajesService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = MensajesService()
        svc.eliminar_historial_chatbot(user["idUsuario"])
        return JsonResponse({"success": True}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotEncuestaResource(View):
    def post(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        payload, status = _get_patient_service().save_chatbot_survey(user["idUsuario"], parse_json_body(request)[0] or {})
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotConfigResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        if not ChatbotConfigService:
            return JsonResponse({"success": True, "config": {
                "max_tokens": 600,
                "max_tokens_user": 1000,
                "daily_message_limit": 20,
            }}, status=200)
        svc = ChatbotConfigService()
        config_data, _ = svc.get_config()
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
            from django.http import StreamingHttpResponse
            def error_stream():
                yield "event: auth-error\ndata: {\"message\": \"No autorizado\"}\n\n"
            return StreamingHttpResponse(error_stream(), content_type="text/event-stream", status=200)

        from django.http import StreamingHttpResponse
        from queue import Empty
        import queue

        if not chatbot_config_events:
            def error_stream():
                yield "event: error\ndata: {\"message\": \"Servicio no disponible\"}\n\n"
            return StreamingHttpResponse(error_stream(), content_type="text/event-stream", status=200)

        q = chatbot_config_events.subscribe()

        def stream():
            try:
                yield ": conectado\n\n"
                while True:
                    try:
                        event = q.get(timeout=60)
                        yield f"event: chatbot-config\ndata: {event}\n\n"
                    except Empty:
                        yield ": keep-alive\n\n"
            finally:
                chatbot_config_events.unsubscribe(q)

        return StreamingHttpResponse(stream(), content_type="text/event-stream")


@method_decorator(csrf_exempt, name="dispatch")
class ConsentimientoChatbotResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        payload, status = _get_patient_service().get_chatbot_consent(user["idUsuario"])
        return JsonResponse(payload, status=status)

    def post(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        data, err = parse_json_body(request)
        if err:
            return err
        consent = bool(data.get("consentimiento_chatbot"))
        payload, status = _get_patient_service().update_chatbot_consent(user["idUsuario"], consent)
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class DocumentoPacienteResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        if not DocumentoService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = DocumentoService()
        payload = svc.list_patient_dashboard(user["idUsuario"])
        return JsonResponse(payload, status=200 if payload.get("success") else 500)

    def post(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        if not DocumentoService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = DocumentoService()
        file = request.FILES.get("archivo")
        descripcion = request.POST.get("descripcion", "")
        payload, status = svc.upload_patient_doc(user["idUsuario"], file, descripcion)
        return JsonResponse(payload, status=status)

    def delete(self, request, id_documento=None):
        user, err = require_role(request, "paciente")
        if err:
            return err
        if not DocumentoService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = DocumentoService()
        payload, status = svc.delete_patient_doc(id_documento, user["idUsuario"])
        return JsonResponse(payload, status=status)

    def patch(self, request, id_documento=None):
        user, err = require_role(request, "paciente")
        if err:
            return err
        if not DocumentoService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = DocumentoService()
        data, _ = parse_json_body(request)
        if data is None:
            data = {}
        professional_id = data.get("profesionalId") or request.GET.get("profesionalId")
        if professional_id:
            professional_id = int(professional_id)
        autorizar = data.get("autorizar")
        if not professional_id and autorizar is None:
            return JsonResponse({"success": False, "message": "Falta profesionalId o autorizar"}, status=400)
        if autorizar is None:
            payload, status = svc.toggle_autorizacion(id_documento, user["idUsuario"], professional_id)
        elif autorizar:
            payload, status = svc.autorizar_documento(id_documento, user["idUsuario"], professional_id)
        else:
            payload, status = svc.desautorizar_documento(id_documento, user["idUsuario"], professional_id)
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class ChatContactoResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err
        if not MensajesService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        from django.conf import settings
        msg_svc = MensajesService()
        payload, _ = _get_patient_service().list_professionals()
        profesionales = payload.get("profesionales", [])
        upload_dir = os.path.join(settings.STATICFILES_DIRS[0], "uploads")
        for p in profesionales:
            fp = p.get("fotoPerfil")
            if fp and not os.path.exists(os.path.join(upload_dir, fp)):
                p["fotoPerfil"] = None
        resultado = msg_svc.get_contactos_con_mensajes(user["idUsuario"], profesionales)
        return JsonResponse({"success": True, "profesionales": resultado}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class ChatMensajeResource(View):
    def get(self, request):
        user, err = require_auth(request)
        if err:
            return err
        if not MensajesService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        id_receptor = int(request.GET.get("receptor") or 0)
        if not id_receptor:
            return JsonResponse({"success": False, "message": "Falta receptor"}, status=400)
        svc = MensajesService()
        desde = int(request.GET.get("desde", 0))
        msgs = svc.get_mensajes(user["idUsuario"], id_receptor, desde)
        return JsonResponse({"success": True, "mensajes": msgs}, status=200)

    def post(self, request):
        user, err = require_auth(request)
        if err:
            return err
        if not MensajesService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = MensajesService()
        data, err = parse_json_body(request)
        if err:
            return err
        receptor = data.get("receptor")
        mensaje = (data.get("mensaje") or "").strip()
        if not receptor or not mensaje:
            return JsonResponse({"success": False, "message": "Datos incompletos"}, status=400)
        if len(mensaje) > 2000:
            return JsonResponse({"success": False, "message": "Mensaje demasiado largo"}, status=400)
        id_msg = svc.enviar_mensaje(user["idUsuario"], receptor, mensaje)
        return JsonResponse({"success": True, "idMensaje": id_msg}, status=201)
