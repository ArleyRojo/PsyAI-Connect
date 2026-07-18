import json
import os

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.views import View

from apps.core.permissions import require_auth, require_role
from apps.documents.services import DocumentoService

documento_service = DocumentoService()


class DocumentoProfesionalListView(View):
    def get(self, request, id_paciente):
        user, err = require_auth(request)
        if err:
            return err
        payload, status = documento_service.list_patient_docs(user["idUsuario"], id_paciente)
        return JsonResponse(payload, status=status)

    def post(self, request, id_paciente):
        user, err = require_auth(request)
        if err:
            return err
        file = request.FILES.get("archivo")
        if not file:
            return JsonResponse({"success": False, "message": "No se proporcionó archivo"}, status=400)
        categoria = request.POST.get("categoria")
        visibilidad = request.POST.get("visibilidad")
        notas = request.POST.get("notasInternas")
        payload, status = documento_service.upload_profesional_doc(
            user["idUsuario"], id_paciente, file, categoria, visibilidad, notas,
        )
        return JsonResponse(payload, status=status)


class DocumentoProfesionalDetailView(View):
    def patch(self, request, id_documento):
        user, err = require_auth(request)
        if err:
            return err
        payload, status = documento_service.toggle_doc_visibility(id_documento, user["idUsuario"])
        return JsonResponse(payload, status=status)

    def delete(self, request, id_documento):
        user, err = require_auth(request)
        if err:
            return err
        payload, status = documento_service.delete_profesional_doc(id_documento, user["idUsuario"])
        return JsonResponse(payload, status=status)


class DocumentoProfesionalDownloadView(View):
    def get(self, request, id_documento):
        user, err = require_auth(request)
        if err:
            return err
        doc, err_payload, status = documento_service.get_profesional_doc_for_download(id_documento, user["idUsuario"])
        if err_payload:
            return JsonResponse(err_payload, status=status)
        return self._serve_file(doc)

    def _serve_file(self, doc):
        static_root = settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else os.path.join(settings.BASE_DIR, "static")
        file_path = os.path.join(static_root, doc["rutaArchivo"])
        if not os.path.isfile(file_path):
            raise Http404
        response = FileResponse(open(file_path, "rb"))
        response["Content-Disposition"] = f'inline; filename="{doc["nombreArchivo"]}"'
        return response


class DocumentoPacienteDashboardView(View):
    def get(self, request):
        user, err = require_auth(request)
        if err:
            return err
        payload = documento_service.list_patient_dashboard(user["idUsuario"])
        return JsonResponse(payload, status=200)


class DocumentoPacienteOwnListView(View):
    def get(self, request):
        user, err = require_auth(request)
        if err:
            return err
        docs = documento_service.repo.list_patient_own_docs(user["idUsuario"])
        for d in docs:
            d["tamano"] = documento_service._format_size(d.get("tamanoArchivo"))
            d["fecha"] = documento_service._format_date(d.get("fecha"))
        return JsonResponse({"success": True, "documentos": docs}, status=200)

    def post(self, request):
        user, err = require_auth(request)
        if err:
            return err
        file = request.FILES.get("archivo")
        if not file:
            return JsonResponse({"success": False, "message": "No se proporcionó archivo"}, status=400)
        descripcion = request.POST.get("descripcion")
        payload, status = documento_service.upload_patient_doc(user["idUsuario"], file, descripcion)
        return JsonResponse(payload, status=status)


class DocumentoPacienteOwnDetailView(View):
    def delete(self, request, id_documento):
        user, err = require_auth(request)
        if err:
            return err
        payload, status = documento_service.delete_patient_doc(id_documento, user["idUsuario"])
        return JsonResponse(payload, status=status)


class DocumentoPacienteDownloadView(View):
    def get(self, request, id_documento):
        user, err = require_auth(request)
        if err:
            return err
        doc, err_payload, status = documento_service.get_patient_doc_for_download(
            id_documento, user["idUsuario"], user["rol"],
        )
        if err_payload:
            return JsonResponse(err_payload, status=status)
        return self._serve_file(doc)

    def _serve_file(self, doc):
        static_root = settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else os.path.join(settings.BASE_DIR, "static")
        file_path = os.path.join(static_root, doc["rutaArchivo"])
        if not os.path.isfile(file_path):
            raise Http404
        response = FileResponse(open(file_path, "rb"))
        response["Content-Disposition"] = f'inline; filename="{doc["nombreArchivo"]}"'
        return response


class AutorizacionToggleView(View):
    def post(self, request, id_documento):
        user, err = require_auth(request)
        if err:
            return err
        data = {}
        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            pass
        patient_id = data.get("idPaciente") or user["idUsuario"]
        payload, status = documento_service.toggle_autorizacion(id_documento, patient_id, user["idUsuario"])
        return JsonResponse(payload, status=status)
