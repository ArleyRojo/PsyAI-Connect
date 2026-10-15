import logging

from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import (
    IsAuthenticatedDRF,
    IsPaciente,
    IsPacienteOrProfesional,
    IsProfesional,
)
from apps.scheduling.services import AppointmentService

logger = logging.getLogger(__name__)

appointment_service = AppointmentService()


class CitaViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def list(self, request):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        if user_role == "profesional":
            filtrar = request.query_params.get("filter", "")
            if filtrar == "solicitadas":
                payload, status_code = appointment_service.list_professional_appointments(
                    user_id, pending_only=True,
                )
            else:
                page = int(request.query_params.get("page", 1) or 1)
                limit = int(request.query_params.get("limit", 20) or 20)
                payload, status_code = appointment_service.list_professional_appointments(
                    user_id, page=page, limit=limit,
                )
        elif user_role == "paciente":
            payload, status_code = appointment_service.list_patient_appointments(user_id)
        else:
            return Response(
                {"success": False, "message": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(payload, status=status_code)

    def create(self, request):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        if user_role not in ("paciente", "profesional"):
            return Response(
                {"success": False, "message": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy()
        created_by_professional = data.get("creado_por_profesional", False)

        if user_role == "profesional" and created_by_professional:
            data["idProfesional"] = user_id

        payload, status_code = appointment_service.create_appointment(
            user_id, data,
            created_by_professional=created_by_professional,
        )
        return Response(payload, status=status_code)


class CitaDetailViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedDRF]

    def partial_update(self, request, pk=None):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        if user_role != "profesional":
            return Response(
                {"success": False, "message": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        payload, status_code = appointment_service.update_status(
            pk, data.get("estado"), user_id, extra_data=data
        )
        return Response(payload, status=status_code)

    def destroy(self, request, pk=None):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        if user_role not in ("paciente", "profesional"):
            return Response(
                {"success": False, "message": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data if request.data else {}
        motivo = data.get("motivoCancelacion", "").strip()

        if user_role == "profesional":
            payload, status_code = appointment_service.cancel_professional_appointment(
                pk, user_id, motivo,
            )
        else:
            payload, status_code = appointment_service.cancel_appointment(
                pk, user_id, motivo,
            )
        return Response(payload, status=status_code)


class CitaDisponibleResource(APIView):
    permission_classes = []

    def get(self, request):
        path = request.path
        if "fechas-disponibles" in path:
            id_profesional = request.query_params.get("idProfesional")
            anio = request.query_params.get("anio")
            mes = request.query_params.get("mes")
            payload, status_code = appointment_service.get_available_dates(id_profesional, anio, mes)
        else:
            id_profesional = request.query_params.get("idProfesional")
            fecha = request.query_params.get("fecha")
            payload, status_code = appointment_service.get_available_times(id_profesional, fecha)
        return Response(payload, status=status_code)


class CitaProximaResource(APIView):
    permission_classes = [IsAuthenticatedDRF, IsPaciente]

    def get(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = appointment_service.get_next_patient_appointment(user_id)
        return Response(payload, status=status_code)


class CitaHorarioOcupadoResource(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def get(self, request):
        id_profesional = request.query_params.get("idProfesional")
        fecha = request.query_params.get("fecha")
        payload, status_code = appointment_service.get_taken_slots(id_profesional, fecha)
        return Response(payload, status=status_code)
