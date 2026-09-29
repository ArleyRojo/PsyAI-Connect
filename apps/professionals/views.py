import os
import logging

from django.apps import apps
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAuthenticatedDRF, IsProfesional
from apps.professionals.services import ProfessionalService
from apps.professionals.serializers import (
    PerfilProfesionalSerializer,
    DisponibilidadSerializer,
    DiagnosticoSerializer,
    ReporteCreateSerializer,
    ReporteUpdateSerializer,
    VisibilidadSerializer,
    ChatMensajeSerializer,
)

logger = logging.getLogger(__name__)

if apps.is_installed("apps.documents"):
    from apps.documents.services import DocumentoService
else:
    DocumentoService = None

if apps.is_installed("apps.chatbot"):
    from apps.chatbot.services import ChatEventsServiceManager as MensajesService
else:
    MensajesService = None


def _get_prof_service():
    return ProfessionalService()


class PerfilProfesionalViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def retrieve(self, request, pk=None):
        id_usuario = int(pk)
        payload, status_code = _get_prof_service().get_profile(id_usuario)
        return Response(payload, status=status_code)

    def update(self, request):
        serializer = PerfilProfesionalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user_id = getattr(request, "user_id", None)
        if data.get("idUsuario") and data["idUsuario"] != user_id:
            return Response(
                {"success": False, "message": "No tienes permiso para editar este perfil"},
                status=status.HTTP_403_FORBIDDEN,
            )
        data["idUsuario"] = user_id
        payload, status_code = _get_prof_service().update_profile(data)
        return Response(payload, status=status_code)


class DisponibilidadViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def create(self, request):
        user_role = getattr(request, "user_role", None)
        if user_role != "profesional":
            return Response(
                {"success": False, "message": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DisponibilidadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user_id = getattr(request, "user_id", None)
        logger.info("Disponibilidad POST user=%s data=%s", user_id, data)
        try:
            from apps.scheduling.services import DisponibilidadService
            svc = DisponibilidadService()
            payload, status_code = svc.create_availability(user_id, data)
        except Exception:
            logger.exception("DisponibilidadResource.post ERROR")
            return Response(
                {"success": False, "message": "Error al crear disponibilidad"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(payload, status=status_code)

    def list(self, request):
        user_id = getattr(request, "user_id", None)
        id_profesional = user_id
        try:
            from apps.scheduling.services import DisponibilidadService
            svc = DisponibilidadService()
            payload, status_code = svc.get_availability(id_profesional)
        except Exception:
            logger.exception("Error in DisponibilidadResource.get")
            return Response(
                {"success": True, "disponibilidad": []},
                status=status.HTTP_200_OK,
            )
        return Response(payload, status=status_code)

    def retrieve(self, request, pk=None):
        id_profesional = int(pk)
        try:
            from apps.scheduling.services import DisponibilidadService
            svc = DisponibilidadService()
            payload, status_code = svc.get_availability(id_profesional)
        except Exception:
            logger.exception("Error in DisponibilidadResource.get")
            return Response(
                {"success": True, "disponibilidad": []},
                status=status.HTTP_200_OK,
            )
        return Response(payload, status=status_code)


class DashboardResource(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def get(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_prof_service().get_dashboard(user_id)
        return Response(payload, status=status_code)


class ProfesionalPacienteResource(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def get(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_prof_service().list_patients(user_id)
        return Response(payload, status=status_code)


class DiagnosticoViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def list(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_prof_service().diagnosis_history(user_id)
        return Response(payload, status=status_code)

    def create(self, request):
        serializer = DiagnosticoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_prof_service().save_diagnosis(user_id, serializer.validated_data)
        return Response(payload, status=status_code)


class ReporteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def list(self, request):
        user_id = getattr(request, "user_id", None)
        filter_param = request.query_params.get("filter", "")
        if filter_param == "eliminados":
            payload, status_code = _get_prof_service().get_deleted_reports(user_id)
        else:
            payload, status_code = _get_prof_service().report_overview(user_id)
        return Response(payload, status=status_code)

    def create(self, request):
        serializer = ReporteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_prof_service().create_report(user_id, serializer.validated_data)
        return Response(payload, status=status_code)

    def update(self, request, pk=None):
        serializer = ReporteUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data["idReporte"] = int(pk)
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_prof_service().update_report(user_id, data)
        return Response(payload, status=status_code)

    def destroy(self, request, pk=None):
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_prof_service().delete_report(user_id, int(pk))
        return Response(payload, status=status_code)


class EvolucionProfesionalResource(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def get(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_prof_service().all_evolution(user_id)
        return Response(payload, status=status_code)


class PacienteChatbotHistorialResource(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request, id_paciente=None):
        user_id = getattr(request, "user_id", None)
        payload, status_code = _get_prof_service().get_patient_chatbot_history(user_id, id_paciente)
        return Response(payload, status=status_code)


class DocumentoProfesionalPacienteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def list(self, request, id_paciente=None):
        id_paciente = int(id_paciente) if id_paciente else None
        user_id = getattr(request, "user_id", None)
        if not DocumentoService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = DocumentoService()
        payload = svc.list_patient_docs(user_id, id_paciente)
        return Response(payload, status=200 if payload.get("success") else 500)

    def create(self, request, id_paciente=None):
        id_paciente = int(id_paciente) if id_paciente else None
        user_id = getattr(request, "user_id", None)
        if not DocumentoService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = DocumentoService()
        file = request.FILES.get("archivo")
        categoria = request.data.get("categoria", "Otro")
        visibilidad = request.data.get("visibilidad", "privado")
        notas = request.data.get("notas", "")
        payload, status_code = svc.upload_profesional_doc(
            user_id, id_paciente, file, categoria, visibilidad, notas,
        )
        return Response(payload, status=status_code)

    def partial_update(self, request, pk=None):
        return self._handle_visibilidad(request, int(pk))

    def update(self, request, pk=None):
        return self._handle_visibilidad(request, int(pk))

    def destroy(self, request, pk=None):
        user_id = getattr(request, "user_id", None)
        if not DocumentoService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = DocumentoService()
        payload, status_code = svc.delete_profesional_doc(int(pk), user_id)
        return Response(payload, status=status_code)

    def _handle_visibilidad(self, request, id_documento):
        user_id = getattr(request, "user_id", None)
        if not DocumentoService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = VisibilidadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visibilidad = serializer.validated_data.get("visibilidad")
        if not visibilidad:
            return Response(
                {"success": False, "message": "Falta visibilidad"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        svc = DocumentoService()
        payload, status_code = svc.toggle_doc_visibility(id_documento, user_id)
        return Response(payload, status=status_code)


class DownloadResource(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request, id_documento=None, tipo=None):
        from django.http import FileResponse as DjangoFileResponse

        user_id = getattr(request, "user_id", None)
        user_role = getattr(request, "user_role", None)

        if tipo is None:
            path = request.path
            if "/documento-profesional/" in path:
                tipo = "documento-profesional"
            elif "/documento-paciente/" in path:
                tipo = "documento-paciente"
            else:
                return Response(
                    {"success": False, "message": "Tipo de descarga no especificado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not DocumentoService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        svc = DocumentoService()

        if tipo in ("profesional", "documento-profesional"):
            if user_role != "profesional":
                return Response(
                    {"success": False, "message": "No autorizado"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            doc, err_payload, status_code = svc.get_profesional_doc_for_download(id_documento, user_id)
        elif tipo in ("paciente", "documento-paciente"):
            if user_role not in ("profesional", "paciente"):
                return Response(
                    {"success": False, "message": "No autorizado"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            doc, err_payload, status_code = svc.get_patient_doc_for_download(
                id_documento, user_id, user_role,
            )
        else:
            return Response(
                {"success": False, "message": "Tipo inválido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if err_payload:
            return Response(err_payload, status=status_code)

        file_path = os.path.join(str(settings.MEDIA_ROOT), doc["rutaArchivo"])
        if not os.path.exists(file_path):
            return Response(
                {"success": False, "message": "Archivo no encontrado en el servidor"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return DjangoFileResponse(open(file_path, "rb"), as_attachment=False, filename=doc["nombreArchivo"])


class ChatContactoProfesionalResource(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def get(self, request):
        user_id = getattr(request, "user_id", None)
        if not MensajesService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        msg_svc = MensajesService()
        prof_svc = _get_prof_service()
        pacientes = prof_svc.list_patients_for_chat()
        resultado = msg_svc.get_contactos_con_mensajes(user_id, pacientes, id_field="idUsuario")
        return Response({"success": True, "pacientes": resultado}, status=status.HTTP_200_OK)


class ChatMensajeProfesionalResource(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request):
        user_id = getattr(request, "user_id", None)
        if not MensajesService:
            return Response(
                {"success": False, "message": "Servicio no disponible"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        id_paciente = int(request.query_params.get("receptor") or 0)
        if not id_paciente:
            return Response(
                {"success": False, "message": "Falta receptor"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        svc = MensajesService()
        desde = int(request.query_params.get("desde", 0))
        msgs = svc.get_mensajes(user_id, id_paciente, desde)
        return Response({"success": True, "mensajes": msgs}, status=status.HTTP_200_OK)

    def post(self, request):
        user_id = getattr(request, "user_id", None)
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
        id_msg = svc.enviar_mensaje(user_id, receptor, mensaje)
        return Response({"success": True, "idMensaje": id_msg}, status=status.HTTP_201_CREATED)


class AllPacientesProfesionalResource(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request):
        # Ensure the user is professional or admin
        user_role = getattr(request, "user_role", None)
        if user_role not in ("profesional", "admin"):
            return Response({"success": False, "message": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
        from apps.patients.services import PatientService
        svc = PatientService()
        # Return a large page to get all patients
        payload, status_code = svc.list_patients(page=1, limit=1000)
        return Response(payload, status=status_code)


class PacienteAsignarResource(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def post(self, request, id_paciente):
        from apps.professionals.models import PacientesProfesional
        user_id = getattr(request, "user_id", None)
        PacientesProfesional.objects.get_or_create(
            idProfesional_id=user_id,
            idPaciente_id=id_paciente,
        )
        return Response(
            {"success": True, "message": "Paciente asignado correctamente"},
            status=status.HTTP_200_OK,
        )

