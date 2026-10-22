import json
import logging
import os
from decimal import Decimal
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse, FileResponse, Http404
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
from apps.billing.models import Facturas

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

        # Solo profesional puede crear
        if user_role != "profesional":
            return Response(
                {"success": False, "message": "No autorizado para crear facturas"},
                status=drf_status.HTTP_403_FORBIDDEN,
            )

# parse multipart data (DRF puts form fields in request.data)
        data = request.data
        items_raw = data.get("items")
        if not items_raw:
            return Response({"success": False, "message": "Debes incluir items"}, status=drf_status.HTTP_400_BAD_REQUEST)
        if isinstance(items_raw, list):
            items = items_raw
        else:
            try:
                import json
                items = json.loads(items_raw)
            except Exception:
                return Response({"success": False, "message": "Items inválidos"}, status=drf_status.HTTP_400_BAD_REQUEST)

        if not isinstance(items, list) or not items:
            return Response({"success": False, "message": "Debes incluir al menos un item"}, status=drf_status.HTTP_400_BAD_REQUEST)
        for it in items:
            if not it.get("descripcion") or it.get("precioUnitario") in (None, ""):
                return Response({"success": False, "message": "Cada item debe tener descripción y precio unitario"}, status=drf_status.HTTP_400_BAD_REQUEST)
            try:
                precio = Decimal(it["precioUnitario"])
                if precio <= 0:
                    raise ValueError
            except Exception:
                return Response({"success": False, "message": "Precio unitario inválido"}, status=drf_status.HTTP_400_BAD_REQUEST)

        id_paciente = data.get("idPaciente")
        if not id_paciente:
            return Response({"success": False, "message": "Debes especificar el paciente"}, status=drf_status.HTTP_400_BAD_REQUEST)

        cita_id = data.get("idCita") or None
        fechaPago = data.get("fechaPago")
        if not fechaPago:
            return Response({"success": False, "message": "Fecha de pago obligatoria"}, status=drf_status.HTTP_400_BAD_REQUEST)
        metodoPago = data.get("metodoPago")
        if not metodoPago:
            return Response({"success": False, "message": "Método de pago obligatorio"}, status=drf_status.HTTP_400_BAD_REQUEST)
        referencia = data.get("referencia", "")
        notas = data.get("notas", "")
        evidencia = request.FILES.get("evidencia")

        payload, status_code = invoice_service.create_invoice(
            professional_user_id=user_id,
            patient_id=id_paciente,
            cita_id=cita_id,
            items=items,
            fechaPago=fechaPago,
            metodoPago=metodoPago,
            referencia=referencia,
            notas=notas,
            evidencia=evidencia,
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

        # Solo el profesional dueño puede anular
        if user_role != "profesional":
            return Response(
                {"success": False, "message": "No autorizado para anular facturas"},
                status=drf_status.HTTP_403_FORBIDDEN,
            )

        data = request.data if isinstance(request.data, dict) else {}

        # anular
        if data.get("anular") or data.get("motivoAnulacion"):
            motivo = data.get("motivoAnulacion", "").strip()
            payload, status_code = invoice_service.annul_invoice(
                id_factura, motivo, user_id, user_role
            )
        else:
            # otros cambios no permitidos
            payload, status_code = {"success": False, "message": "Operación no permitida"}, drf_status.HTTP_400_BAD_REQUEST
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


class FacturaEvidenciaView(APIView):
    permission_classes = [IsAuthenticatedDRF]

    def get(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        user_role = getattr(request, "user_role", None)

        try:
            factura = Facturas.objects.select_related("idPaciente", "idProfesional", "confirmada_por").get(idFactura=id_factura)
        except Facturas.DoesNotExist:
            return Response({"success": False, "message": "Factura no encontrada"}, status=drf_status.HTTP_404_NOT_FOUND)

        # Permisos: paciente dueño, profesional dueño, admin
        if user_role not in ("admin",) and factura.idPaciente_id != user_id and factura.idProfesional_id != user_id:
            return Response({"success": False, "message": "No autorizado"}, status=drf_status.HTTP_403_FORBIDDEN)

        if not factura.evidencia:
            return Response({"success": False, "message": "No hay evidencia disponible"}, status=drf_status.HTTP_404_NOT_FOUND)

        # Verificar que el archivo existe
        if not os.path.exists(factura.evidencia.path):
            return Response({"success": False, "message": "Archivo de evidencia no encontrado"}, status=drf_status.HTTP_404_NOT_FOUND)

        # Servir archivo inline
        response = FileResponse(open(factura.evidencia.path, "rb"), as_attachment=False)
        response["Content-Disposition"] = f'inline; filename="{os.path.basename(factura.evidencia.name)}"'
        return response


class FacturaConfirmarPagoView(APIView):
    permission_classes = [IsAuthenticatedDRF, IsProfesional]

    def post(self, request, id_factura):
        user_id = getattr(request, "user_id", None)
        evidencia = request.FILES.get("evidencia")
        metodo_pago = request.data.get("metodoPago")
        referencia = request.data.get("referencia")
        notas = request.data.get("notas")

        payload, status_code = invoice_service.confirm_payment(
            id_factura,
            professional_user_id=user_id,
            evidencia=evidencia,
            metodoPago=metodo_pago,
            referencia=referencia,
            notas=notas,
        )
        return Response(payload, status=status_code)