import os

from django.apps import apps
from django.conf import settings
from django.views import View
from rest_framework import viewsets, status, generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import (
    IsAuthenticatedDRF,
    IsPaciente,
    IsProfesional,
    IsAdminOrProfesional,
    parse_json_body,
)
from apps.patients.services import PatientService
from apps.patients.serializers import (
    ChatbotEncuestaSerializer,
    ChatbotMessageSerializer,
    ChatMensajeSerializer,
    ConsentimientoSerializer,
    DocumentoAutorizacionSerializer,
    DocumentoUploadSerializer,
    EvolucionSerializer,
    PreferenciasSerializer,
)

if apps.is_installed("apps.chatbot"):
    from apps.chatbot.services import ChatbotService
    from apps.chatbot.services import ChatEventsServiceManager as MensajesService
    from apps.chatbot.services import ChatbotConfigService, chatbot_config_events
else:
    ChatbotService = None
    MensajesService = None
    ChatbotConfigService = None
    chatbot_config_events = None

if apps.is_installed("apps.documents"):
    from apps.documents.services import DocumentoService
else:
    DocumentoService = None


def _get_patient_service():
    return PatientService()


class PerfilPacienteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def retrieve(self, request, pk=None):
        id_usuario = int(pk)
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)
        if user_role not in ("admin", "profesional") and user_id != id_usuario:
            return Response(
                {"success": False, "message": "No autorizado"}, status=status.HTTP_403_FORBIDDEN
            )
        payload, status_code = _get_patient_service().get_patient_profile(id_usuario)
        return Response(payload, status=status_code)

    def update(self, request, pk=None):
        user_role = getattr(request, "user_role", None)
        if user_role != "paciente":
            return Response(
                {"success": False, "message": "No autorizado"}, status=status.HTTP_403_FORBIDDEN
            )
        data = request.data.copy()
        data["idUsuario"] = getattr(request, "user_id", None)
        payload, status_code = _get_patient_service().update_patient_profile(data)
        return Response(payload, status=status_code)


class PreferenciasPacienteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def list(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_patient_service().get_preferences(user_id)
        return Response(payload, status=status_code)

    def update(self, request):
        user_id = getattr(request, "user_id", None)
        data = request.data.copy()
        payload, status_code = _get_patient_service().save_preferences(user_id, data)
        return Response(payload, status=status_code)


class PerfilFotoViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def update(self, request):
        user_id = getattr(request, "user_id", None)
        file = request.FILES.get("foto") or request.FILES.get("fotoPerfil")
        payload, status_code = _get_patient_service().update_profile_photo(user_id, file)
        if payload.get("success") and payload.get("fotoPerfil"):
            request.session["fotoPerfil"] = payload["fotoPerfil"]
            if "usuario" in request.session and isinstance(request.session["usuario"], dict):
                request.session["usuario"]["fotoPerfil"] = payload["fotoPerfil"]
            request.session.modified = True
        return Response(payload, status=status_code)

    def create(self, request):
        return self.update(request)


class EvolucionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def list(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_patient_service().get_evolution_history(user_id)
        return Response(payload, status=status_code)

    def create(self, request):
        user_id = getattr(request, "user_id", None)
        data = request.data.copy()
        payload, status_code = _get_patient_service().save_evolution(user_id, data)
        return Response(payload, status=status_code)


class PacienteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsAdminOrProfesional]

    def list(self, request):
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))
        payload, status_code = _get_patient_service().list_patients(page, limit)
        return Response(payload, status=status_code)


class ProfesionalViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def list(self, request):
        payload, status_code = _get_patient_service().list_professionals()
        return Response(payload, status=status_code)


class ChatbotAPIView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def post(self, request):
        if not ChatbotService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        data = request.data.copy()
        svc = ChatbotService()
        payload, status_code = svc.build_response(
            getattr(request, "user_id", None), data.get("mensaje")
        )
        return Response(payload, status=status_code)

    def get(self, request):
        if not ChatbotService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = ChatbotService()
        payload, status_code = svc.get_history(getattr(request, "user_id", None))
        return Response(payload, status=status_code)

    def delete(self, request):
        if not MensajesService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = MensajesService()
        svc.eliminar_historial_chatbot(getattr(request, "user_id", None))
        return Response({"success": True}, status=status.HTTP_200_OK)


class ChatbotEncuestaViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def create(self, request):
        user_id = getattr(request, "user_id", None)
        serializer = ChatbotEncuestaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = _get_patient_service().save_chatbot_survey(
            user_id, serializer.validated_data
        )
        return Response(payload, status=status_code)


class ChatbotConfigViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def list(self, request):
        if not ChatbotConfigService:
            return Response(
                {
                    "success": True,
                    "config": {
                        "max_tokens": 600,
                        "max_tokens_user": 1000,
                        "daily_message_limit": 20,
                    },
                },
                status=status.HTTP_200_OK,
            )
        svc = ChatbotConfigService()
        config_data, _ = svc.get_config()
        return Response(
            {
                "success": True,
                "config": {
                    "max_tokens": config_data.get("config", {}).get("max_tokens", 600),
                    "max_tokens_user": config_data.get("config", {}).get("max_tokens_user", 1000),
                    "daily_message_limit": config_data.get("config", {}).get("daily_message_limit", 20),
                },
            },
            status=status.HTTP_200_OK,
        )


class ChatbotConfigEventsResource(View):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def get(self, request):
        from django.http import StreamingHttpResponse
        from queue import Empty
        from apps.authentication.models import Register

        if not chatbot_config_events:
            def error_stream():
                yield 'event: error\ndata: {"message": "Servicio no disponible"}\n\n'
            return StreamingHttpResponse(error_stream(), content_type="text/event-stream", status=200)

        q = chatbot_config_events.subscribe()
        user_id = request.session.get("idUsuario")

        def stream():
            try:
                yield ": conectado\n\n"
                while True:
                    # Verify account status each iteration
                    if user_id:
                        try:
                            usr = Register.objects.only("activo", "estadoCuenta").get(pk=user_id)
                            if not usr.activo or usr.estadoCuenta != "Activa":
                                yield f"event: account_suspended\ndata: {json.dumps({'message': 'Tu cuenta ha sido suspendida. Contacta al administrador.'})}\n\n"
                                return
                        except Register.DoesNotExist:
                            yield f"event: account_suspended\ndata: {json.dumps({'message': 'Tu cuenta ha sido suspendida. Contacta al administrador.'})}\n\n"
                            return
                    try:
                        event = q.get(timeout=60)
                        yield f"event: chatbot-config\ndata: {event}\n\n"
                    except Empty:
                        yield ": keep-alive\n\n"
            finally:
                chatbot_config_events.unsubscribe(q)

        return StreamingHttpResponse(stream(), content_type="text/event-stream")


class ConsentimientoChatbotViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def list(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_patient_service().get_chatbot_consent(user_id)
        return Response(payload, status=status_code)

    def create(self, request):
        user_id = getattr(request, "user_id", None)
        serializer = ConsentimientoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consent = serializer.validated_data["consentimiento_chatbot"]
        payload, status_code = _get_patient_service().update_chatbot_consent(user_id, consent)
        return Response(payload, status=status_code)


class DocumentoPacienteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def list(self, request):
        if not DocumentoService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = DocumentoService()
        payload = svc.list_patient_dashboard(getattr(request, "user_id", None))
        return Response(payload, status=200 if payload.get("success") else 500)

    def create(self, request):
        if not DocumentoService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = DocumentoService()
        file = request.FILES.get("archivo")
        descripcion = request.data.get("descripcion", "")
        payload, status_code = svc.upload_patient_doc(
            getattr(request, "user_id", None), file, descripcion
        )
        return Response(payload, status=status_code)

    def destroy(self, request, pk=None):
        if not DocumentoService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = DocumentoService()
        payload, status_code = svc.delete_patient_doc(int(pk), getattr(request, "user_id", None))
        return Response(payload, status=status_code)

    def partial_update(self, request, pk=None):
        if not DocumentoService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = DocumentoService()
        data = request.data.copy()
        professional_id = data.get("profesionalId") or request.query_params.get("profesionalId")
        if professional_id:
            professional_id = int(professional_id)
        autorizar = data.get("autorizar")
        user_id = getattr(request, "user_id", None)
        if not professional_id and autorizar is None:
            return Response(
                {"success": False, "message": "Falta profesionalId o autorizar"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if autorizar is None:
            payload, status_code = svc.toggle_autorizacion(int(pk), user_id, professional_id)
        elif autorizar:
            payload, status_code = svc.autorizar_documento(int(pk), user_id, professional_id)
        else:
            payload, status_code = svc.desautorizar_documento(int(pk), user_id, professional_id)
        return Response(payload, status=status_code)


class ChatContactoViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def list(self, request):
        if not MensajesService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        user_id = getattr(request, "user_id", None)
        msg_svc = MensajesService()
        payload, _ = _get_patient_service().list_professionals()
        profesionales = payload.get("profesionales", [])
        upload_dir = os.path.join(settings.STATICFILES_DIRS[0], "uploads")
        for p in profesionales:
            fp = p.get("fotoPerfil")
            if fp and not os.path.exists(os.path.join(upload_dir, fp)):
                p["fotoPerfil"] = None
        resultado = msg_svc.get_contactos_con_mensajes(user_id, profesionales)
        return Response({"success": True, "profesionales": resultado}, status=status.HTTP_200_OK)


class ChatMensajeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def list(self, request):
        if not MensajesService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        id_receptor = int(request.query_params.get("receptor") or 0)
        if not id_receptor:
            return Response(
                {"success": False, "message": "Falta receptor"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        svc = MensajesService()
        desde = int(request.query_params.get("desde", 0))
        user_id = getattr(request, "user_id", None)
        msgs = svc.get_mensajes(user_id, id_receptor, desde)
        return Response({"success": True, "mensajes": msgs}, status=status.HTTP_200_OK)

    def create(self, request):
        if not MensajesService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = ChatMensajeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receptor = serializer.validated_data["receptor"]
        mensaje = serializer.validated_data["mensaje"].strip()
        if not receptor or not mensaje:
            return Response(
                {"success": False, "message": "Datos incompletos"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        svc = MensajesService()
        user_id = getattr(request, "user_id", None)
        id_msg = svc.enviar_mensaje(user_id, receptor, mensaje)
        return Response({"success": True, "idMensaje": id_msg}, status=status.HTTP_201_CREATED)


def _get_patient_service():
    return PatientService()


class AnamnesisViewSet(viewsets.ViewSet):
    """
    CRUD de Anamnesis clínica.
    Permisos: profesional o admin autenticado.
    URL base: /api/paciente/<paciente_id>/anamnesis
    """
    permission_classes = [IsAuthenticatedDRF, IsAdminOrProfesional]

    def retrieve(self, request, paciente_id=None):
        profesional_id = getattr(request, "user_id", None)
        payload, status_code = _get_patient_service().get_anamnesis(paciente_id, profesional_id)
        return Response(payload, status=status_code)

    def create(self, request, paciente_id=None):
        profesional_id = getattr(request, "user_id", None)
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        payload, status_code = _get_patient_service().registrar_anamnesis(
            paciente_id, profesional_id, data
        )
        return Response(payload, status=status_code)

    def update(self, request, paciente_id=None):
        profesional_id = getattr(request, "user_id", None)
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        payload, status_code = _get_patient_service().actualizar_anamnesis(
            paciente_id, profesional_id, data
        )
        return Response(payload, status=status_code)

    def destroy(self, request, paciente_id=None):
        profesional_id = getattr(request, "user_id", None)
        payload, status_code = _get_patient_service().eliminar_anamnesis(paciente_id, profesional_id)
        return Response(payload, status=status_code)

