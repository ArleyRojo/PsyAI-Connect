import os
import json
import logging

from django.http import JsonResponse, StreamingHttpResponse, FileResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings

from apps.core.permissions import parse_json_body, require_auth, require_role
from apps.professionals.services import ProfessionalService

logger = logging.getLogger(__name__)

try:
    from apps.documents.services import DocumentoService
except ImportError:
    DocumentoService = None

try:
    from apps.chatbot.services import ChatEventsServiceManager as MensajesService
except ImportError:
    MensajesService = None


def _get_prof_service():
    return ProfessionalService()


@method_decorator(csrf_exempt, name="dispatch")
class PerfilProfesionalResource(View):
    def get(self, request, id_usuario=None):
        user, err = require_role(request, "admin", "profesional", "paciente")
        if err:
            return err
        payload, status = _get_prof_service().get_profile(id_usuario)
        return JsonResponse(payload, status=status)

    def put(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        data, err = parse_json_body(request)
        if err:
            return err
        if data.get("idUsuario") and data["idUsuario"] != user["idUsuario"]:
            return JsonResponse({"success": False, "message": "No tienes permiso para editar este perfil"}, status=403)
        data["idUsuario"] = user["idUsuario"]
        payload, status = _get_prof_service().update_profile(data)
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class DisponibilidadResource(View):
    def post(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        data, err = parse_json_body(request)
        if err:
            return err
        logger.info("Disponibilidad POST user=%s data=%s", user.get("idUsuario"), data)
        try:
            from apps.scheduling.services import DisponibilidadService
            svc = DisponibilidadService()
            payload, status = svc.create_availability(user["idUsuario"], data)
        except Exception:
            logger.exception("DisponibilidadResource.post ERROR")
            return JsonResponse({"success": False, "message": "Error al crear disponibilidad"}, status=500)
        return JsonResponse(payload, status=status)

    def get(self, request, id_profesional=None):
        user, err = require_role(request, "admin", "profesional", "paciente")
        if err:
            return err
        if not id_profesional:
            id_profesional = user["idUsuario"]
        try:
            from apps.scheduling.services import DisponibilidadService
            svc = DisponibilidadService()
            payload, status = svc.get_availability(id_profesional)
        except Exception as e:
            logger.exception("Error in DisponibilidadResource.get")
            return JsonResponse({"success": True, "disponibilidad": []}, status=200)
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class DashboardResource(View):
    def get(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        payload, status = _get_prof_service().get_dashboard(user["idUsuario"])
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class ProfesionalPacienteResource(View):
    def get(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        payload, status = _get_prof_service().list_patients(user["idUsuario"])
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class DiagnosticoResource(View):
    def get(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        payload, status = _get_prof_service().diagnosis_history(user["idUsuario"])
        return JsonResponse(payload, status=status)

    def post(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        payload, status = _get_prof_service().save_diagnosis(user["idUsuario"], parse_json_body(request)[0] or {})
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class ReporteResource(View):
    def get(self, request, id_reporte=None):
        user, err = require_role(request, "profesional")
        if err:
            return err
        filter_param = request.GET.get("filter", "")
        if filter_param == "eliminados":
            payload, status = _get_prof_service().get_deleted_reports(user["idUsuario"])
        else:
            payload, status = _get_prof_service().report_overview(user["idUsuario"])
        return JsonResponse(payload, status=status)

    def post(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        payload, status = _get_prof_service().create_report(user["idUsuario"], parse_json_body(request)[0] or {})
        return JsonResponse(payload, status=status)

    def put(self, request, id_reporte=None):
        user, err = require_role(request, "profesional")
        if err:
            return err
        data, err = parse_json_body(request)
        if err:
            return err
        data["idReporte"] = id_reporte
        payload, status = _get_prof_service().update_report(user["idUsuario"], data)
        return JsonResponse(payload, status=status)

    def delete(self, request, id_reporte=None):
        user, err = require_role(request, "profesional")
        if err:
            return err
        payload, status = _get_prof_service().delete_report(user["idUsuario"], id_reporte)
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class EvolucionProfesionalResource(View):
    def get(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        payload, status = _get_prof_service().all_evolution(user["idUsuario"])
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class PacienteChatbotHistorialResource(View):
    def get(self, request, id_paciente=None):
        user, err = require_role(request, "profesional", "admin")
        if err:
            return err
        payload, status = _get_prof_service().get_patient_chatbot_history(user["idUsuario"], id_paciente)
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class DocumentoProfesionalPacienteResource(View):
    def get(self, request, id_paciente=None, id_documento=None):
        user, err = require_role(request, "profesional")
        if err:
            return err
        if not DocumentoService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = DocumentoService()
        payload = svc.list_patient_docs(user["idUsuario"], id_paciente)
        return JsonResponse(payload, status=200 if payload.get("success") else 500)

    def post(self, request, id_paciente=None, id_documento=None):
        user, err = require_role(request, "profesional")
        if err:
            return err
        if not DocumentoService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = DocumentoService()
        file = request.FILES.get("archivo")
        categoria = request.POST.get("categoria", "Otro")
        visibilidad = request.POST.get("visibilidad", "privado")
        notas = request.POST.get("notas", "")
        payload, status = svc.upload_profesional_doc(
            user["idUsuario"], id_paciente, file, categoria, visibilidad, notas,
        )
        return JsonResponse(payload, status=status)

    def _handle_visibilidad(self, request, id_documento):
        user, err = require_role(request, "profesional")
        if err:
            return err
        if not DocumentoService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = DocumentoService()
        data, err = parse_json_body(request)
        if err:
            return err
        visibilidad = data.get("visibilidad")
        if not visibilidad:
            return JsonResponse({"success": False, "message": "Falta visibilidad"}, status=400)
        payload, status = svc.toggle_doc_visibility(id_documento, user["idUsuario"])
        return JsonResponse(payload, status=status)

    def patch(self, request, id_paciente=None, id_documento=None):
        return self._handle_visibilidad(request, id_documento)

    def put(self, request, id_paciente=None, id_documento=None):
        return self._handle_visibilidad(request, id_documento)

    def delete(self, request, id_paciente=None, id_documento=None):
        user, err = require_role(request, "profesional")
        if err:
            return err
        if not DocumentoService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = DocumentoService()
        payload, status = svc.delete_profesional_doc(id_documento, user["idUsuario"])
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class DownloadResource(View):
    def get(self, request, id_documento=None, tipo=None):
        user, err = require_auth(request)
        if err:
            return err
        if tipo is None:
            path = request.path
            if "/documento-profesional/" in path:
                tipo = "documento-profesional"
            elif "/documento-paciente/" in path:
                tipo = "documento-paciente"
            else:
                return JsonResponse({"success": False, "message": "Tipo de descarga no especificado"}, status=400)

        if not DocumentoService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        svc = DocumentoService()

        if tipo in ("profesional", "documento-profesional"):
            if user["rol"] != "profesional":
                return JsonResponse({"success": False, "message": "No autorizado"}, status=403)
            doc, err_payload, status = svc.get_profesional_doc_for_download(id_documento, user["idUsuario"])
        elif tipo in ("paciente", "documento-paciente"):
            if user["rol"] not in ("profesional", "paciente"):
                return JsonResponse({"success": False, "message": "No autorizado"}, status=403)
            doc, err_payload, status = svc.get_patient_doc_for_download(
                id_documento, user["idUsuario"], user["rol"],
            )
        else:
            return JsonResponse({"success": False, "message": "Tipo inválido"}, status=400)

        if err_payload:
            return JsonResponse(err_payload, status=status)

        file_path = os.path.join(str(settings.MEDIA_ROOT), doc["rutaArchivo"])
        if not os.path.exists(file_path):
            return JsonResponse({"success": False, "message": "Archivo no encontrado en el servidor"}, status=404)
        return FileResponse(open(file_path, "rb"), as_attachment=False, filename=doc["nombreArchivo"])


@method_decorator(csrf_exempt, name="dispatch")
class ChatContactoProfesionalResource(View):
    def get(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err
        if not MensajesService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        msg_svc = MensajesService()
        prof_svc = _get_prof_service()
        pacientes = prof_svc.list_patients_for_chat()
        resultado = msg_svc.get_contactos_con_mensajes(user["idUsuario"], pacientes, id_field="idUsuario")
        return JsonResponse({"success": True, "pacientes": resultado}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class ChatMensajeProfesionalResource(View):
    def get(self, request):
        user, err = require_auth(request)
        if err:
            return err
        if not MensajesService:
            return JsonResponse({"success": False, "message": "Servicio no disponible"}, status=503)
        id_paciente = int(request.GET.get("receptor") or 0)
        if not id_paciente:
            return JsonResponse({"success": False, "message": "Falta receptor"}, status=400)
        svc = MensajesService()
        desde = int(request.GET.get("desde", 0))
        msgs = svc.get_mensajes(user["idUsuario"], id_paciente, desde)
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
