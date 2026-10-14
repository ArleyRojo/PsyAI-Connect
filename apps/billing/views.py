import json
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from datetime import datetime

from apps.billing.services import InvoiceService
from apps.billing.repositories import InvoiceRepository
from apps.core.permissions import IsAuthenticatedDRF, IsPaciente, IsProfesional, IsAdmin

logger = logging.getLogger(__name__)

invoice_service = InvoiceService()
invoice_repo = InvoiceRepository()


class FacturaListView(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        if user_role == "paciente":
            estado = request.query_params.get("estado")
            profesional = request.query_params.get("profesional")
            fecha_desde = request.query_params.get("fecha_desde")
            fecha_hasta = request.query_params.get("fecha_hasta")
            payload, status_code = invoice_service.list_patient_invoices(
                user_id,
                estado=estado,
                profesional=profesional,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )
        elif user_role == "profesional":
            estado = request.query_params.get("estado")
            paciente = request.query_params.get("paciente")
            fecha_desde = request.query_params.get("fecha_desde")
            fecha_hasta = request.query_params.get("fecha_hasta")
            payload, status_code = invoice_service.list_professional_invoices(
                user_id,
                estado=estado,
                paciente=paciente,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )
        elif user_role == "admin":
            payload, status_code = invoice_service.list_all_invoices(
                paciente=request.query_params.get("paciente"),
                profesional=request.query_params.get("profesional"),
                estado=request.query_params.get("estado"),
                fecha_desde=request.query_params.get("fecha_desde"),
                fecha_hasta=request.query_params.get("fecha_hasta"),
            )
        else:
            return Response(
                {"success": False, "message": "No autorizado"},
                status=drf_status.HTTP_403_FORBIDDEN,
            )
        return Response(payload, status=status_code)

    def post(self, request):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        data = request.data if isinstance(request.data, dict) else {}

        if user_role == "paciente":
            id_paciente = user_id
            id_profesional = data.get("idProfesional")
            if not id_profesional:
                return Response(
                    {"success": False, "message": "Debes especificar el profesional"},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
        elif user_role == "profesional":
            id_profesional = user_id
            id_paciente = data.get("idPaciente")
            if not id_paciente:
                return Response(
                    {"success": False, "message": "Debes especificar el paciente"},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
        else:
            # admin no puede crear
            return Response(
                {"success": False, "message": "No autorizado para crear facturas"},
                status=drf_status.HTTP_403_FORBIDDEN,
            )

        payload, status_code = invoice_service.create_invoice(
            id_paciente, id_profesional, data
        )
        return Response(payload, status=status_code)


class FacturaDetailView(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        user_role = getattr(request, "user_role", None)
        payload, status_code = invoice_service.get_invoice(
            id_factura, user_id, user_role
        )
        return Response(payload, status=status_code)

    def patch(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        user_role = getattr(request, "user_role", None)

        data = request.data if isinstance(request.data, dict) else {}

        # anular
        if data.get("anular") or data.get("motivoAnulacion"):
            motivo = data.get("motivoAnulacion", "").strip()
            payload, status_code = invoice_service.annul_invoice(
                id_factura, motivo, user_id, user_role
            )
        else:
            # otros cambios no permitidos (estadoPago se cambia solo via confirmar-pago)
            payload, status_code = {"success": False, "message": "Operación no permitida"}, drf_status.HTTP_400_BAD_REQUEST
        return Response(payload, status=status_code)


class FacturaConfirmarPagoView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def post(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        payload, status_code = invoice_service.confirmar_pago(id_factura, user_id)
        return Response(payload, status=status_code)


class FacturaStatsView(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request):
        user_role = getattr(request, "user_role", None)
        user_id = getattr(request, "user_id", None)

        if user_role == "admin":
            payload, status_code = invoice_service.get_admin_stats()
        elif user_role == "paciente":
            payload, status_code = invoice_service.get_patient_invoice_stats(user_id)
        elif user_role == "profesional":
            payload, status_code = invoice_service.get_professional_patients(user_id)
        else:
            return Response(
                {"success": False, "message": "No autorizado"},
                status=drf_status.HTTP_403_FORBIDDEN,
            )
        return Response(payload, status=status_code)


class ProfesionalPacientesView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def get(self, request):
        user_id = getattr(request, "user_id", None)
        payload, status_code = invoice_service.get_professional_patients(user_id)
        return Response(payload, status=status_code)