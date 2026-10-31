import os

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAuthenticatedDRF, IsPaciente
from apps.documents.services import DocumentoService
from apps.documents.serializers import AutorizacionToggleSerializer

documento_service = DocumentoService()


class DocumentoProfesionalViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def list(self, request, id_paciente=None):
        user_id = getattr(request, "user_id", None)
        result = documento_service.list_patient_docs(user_id, id_paciente)
        if isinstance(result, tuple):
            payload, status_code = result
        else:
            payload = result
            status_code = 200 if payload.get("success") else 403
        return Response(payload, status=status_code)

    def create(self, request, id_paciente=None):
        user_id = getattr(request, "user_id", None)
        file = request.FILES.get("archivo")
        if not file:
            return Response(
                {"success": False, "message": "No se proporcionó archivo"}, status=400
            )
        categoria = request.data.get("categoria")
        visibilidad = request.data.get("visibilidad")
        notas = request.data.get("notasInternas")
        payload, status_code = documento_service.upload_profesional_doc(
            user_id, id_paciente, file, categoria, visibilidad, notas,
        )
        return Response(payload, status=status_code)

    def partial_update(self, request, id_documento=None):
        user_id = getattr(request, "user_id", None)
        payload, status_code = documento_service.toggle_doc_visibility(
            id_documento, user_id
        )
        return Response(payload, status=status_code)

    def destroy(self, request, id_documento=None):
        user_id = getattr(request, "user_id", None)
        payload, status_code = documento_service.delete_profesional_doc(
            id_documento, user_id
        )
        return Response(payload, status=status_code)


class DocumentoProfesionalDownloadView(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request, id_documento):
        user_id = getattr(request, "user_id", None)
        doc, err_payload, status_code = documento_service.get_profesional_doc_for_download(
            id_documento, user_id
        )
        if err_payload:
            return Response(err_payload, status=status_code)
        media_root = str(settings.MEDIA_ROOT)
        file_path = os.path.join(media_root, doc["rutaArchivo"])
        if not os.path.isfile(file_path):
            raise Http404
        response = FileResponse(open(file_path, "rb"))
        response["Content-Disposition"] = (
            f'inline; filename="{doc["nombreArchivo"]}"'
        )
        return response


class DocumentoPacienteDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def list(self, request):
        user_id = getattr(request, "user_id", None)
        payload = documento_service.list_patient_dashboard(user_id)
        return Response(payload, status=200 if payload.get("success") else 500)


class DocumentoPacienteOwnViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def list(self, request):
        user_id = getattr(request, "user_id", None)
        docs = documento_service.repo.list_patient_own_docs(user_id)
        for d in docs:
            d["tamano"] = documento_service._format_size(d.get("tamanoArchivo"))
            d["fecha"] = documento_service._format_date(d.get("fecha"))
        return Response({"success": True, "documentos": docs}, status=200)

    def create(self, request):
        user_id = getattr(request, "user_id", None)
        file = request.FILES.get("archivo")
        if not file:
            return Response(
                {"success": False, "message": "No se proporcionó archivo"}, status=400
            )
        descripcion = request.data.get("descripcion")
        payload, status_code = documento_service.upload_patient_doc(
            user_id, file, descripcion
        )
        return Response(payload, status=status_code)

    def destroy(self, request, id_documento=None):
        user_id = getattr(request, "user_id", None)
        payload, status_code = documento_service.delete_patient_doc(
            id_documento, user_id
        )
        return Response(payload, status=status_code)


class DocumentoPacienteDownloadView(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request, id_documento):
        user_id = getattr(request, "user_id", None)
        user_role = getattr(request, "user_role", None)
        doc, err_payload, status_code = documento_service.get_patient_doc_for_download(
            id_documento, user_id, user_role,
        )
        if err_payload:
            return Response(err_payload, status=status_code)
        media_root = str(settings.MEDIA_ROOT)
        file_path = os.path.join(media_root, doc["rutaArchivo"])
        if not os.path.isfile(file_path):
            raise Http404
        response = FileResponse(open(file_path, "rb"))
        response["Content-Disposition"] = (
            f'inline; filename="{doc["nombreArchivo"]}"'
        )
        return response


class AutorizacionToggleView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def post(self, request, id_documento):
        user_id = getattr(request, "user_id", None)
        serializer = AutorizacionToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = documento_service.toggle_autorizacion(
            id_documento, user_id, serializer.validated_data["idProfesional"]
        )
        return Response(payload, status=status_code)
