import json
import logging

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.sessions.models import Session

from apps.core.permissions import parse_json_body, require_auth, require_role
from apps.scheduling.services import AppointmentService

logger = logging.getLogger(__name__)

appointment_service = AppointmentService()


@method_decorator(csrf_exempt, name="dispatch")
class CitaListResource(View):
    def get(self, request):
        rol = request.GET.get("rol", request.session.get("rol"))
        filtrar = request.GET.get("filter", "")

        user, err = require_auth(request)
        if err:
            return err

        if user["rol"] not in ("paciente", "profesional", "admin"):
            return JsonResponse({"success": False, "message": "No autorizado"}, status=403)

        if rol == "profesional":
            id_usuario = user["idUsuario"]
            if filtrar == "solicitadas":
                payload, status = appointment_service.list_professional_appointments(
                    id_usuario, pending_only=True,
                )
            else:
                page = int(request.GET.get("page", 1) or 1)
                limit = int(request.GET.get("limit", 20) or 20)
                payload, status = appointment_service.list_professional_appointments(
                    id_usuario, page=page, limit=limit,
                )
        else:
            id_usuario = user["idUsuario"]
            payload, status = appointment_service.list_patient_appointments(id_usuario)
        return JsonResponse(payload, status=status)

    def post(self, request):
        user, err = require_role(request, "paciente", "profesional")
        if err:
            return err

        data, err = parse_json_body(request)
        if err:
            return err
        created_by_professional = data.get("creado_por_profesional", False)

        payload, status = appointment_service.create_appointment(
            user["idUsuario"], data,
            created_by_professional=created_by_professional,
        )
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class CitaDetailResource(View):
    def patch(self, request, id_cita):
        user, err = require_role(request, "profesional")
        if err:
            return err

        data, err = parse_json_body(request)
        if err:
            return err
        payload, status = appointment_service.update_status(
            id_cita, data.get("estado"), user["idUsuario"],
        )
        return JsonResponse(payload, status=status)

    def delete(self, request, id_cita):
        user, err = require_role(request, "paciente", "profesional")
        if err:
            return err

        data, _ = parse_json_body(request)
        if data is None:
            data = {}
        motivo = data.get("motivoCancelacion", "").strip()

        if user["rol"] == "profesional":
            payload, status = appointment_service.cancel_professional_appointment(
                id_cita, user["idUsuario"], motivo,
            )
        else:
            payload, status = appointment_service.cancel_appointment(
                id_cita, user["idUsuario"], motivo,
            )
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class CitaDisponibleResource(View):
    def get(self, request):
        path = request.path
        if "fechas-disponibles" in path:
            id_profesional = request.GET.get("idProfesional")
            anio = request.GET.get("anio")
            mes = request.GET.get("mes")
            payload, status = appointment_service.get_available_dates(id_profesional, anio, mes)
        else:
            id_profesional = request.GET.get("idProfesional")
            fecha = request.GET.get("fecha")
            payload, status = appointment_service.get_available_times(id_profesional, fecha)
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class CitaProximaResource(View):
    def get(self, request):
        user, err = require_role(request, "paciente")
        if err:
            return err

        payload, status = appointment_service.get_next_patient_appointment(user["idUsuario"])
        return JsonResponse(payload, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class CitaHorarioOcupadoResource(View):
    def get(self, request):
        user, err = require_role(request, "profesional")
        if err:
            return err

        id_profesional = request.GET.get("idProfesional")
        fecha = request.GET.get("fecha")
        payload, status = appointment_service.get_taken_slots(id_profesional, fecha)
        return JsonResponse(payload, status=status)
