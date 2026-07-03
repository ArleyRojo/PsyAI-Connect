from flask import Blueprint, jsonify, request, session
from flask.views import MethodView

from app.services.appointment_service import AppointmentService
from app.services.invoice_service import InvoiceService
from app.utils.route_helpers import RouteHelpers


appointment_bp = Blueprint("appointments", __name__)
appointment_service = AppointmentService()


class CitaListResource(MethodView):
    def get(self):
        rol = request.args.get("rol", session.get("rol"))
        filtrar = request.args.get("filter", "")

        err = RouteHelpers.check_role("paciente", "profesional", "admin")
        if err:
            return err

        if rol == "profesional":
            if filtrar == "solicitadas":
                payload, status = appointment_service.list_professional_appointments(
                    session.get("idUsuario"), pending_only=True,
                )
            else:
                page, limit = RouteHelpers.get_pagination()
                payload, status = appointment_service.list_professional_appointments(
                    session.get("idUsuario"), page=page, limit=limit,
                )
        else:
            page, limit = RouteHelpers.get_pagination()
            payload, status = appointment_service.list_patient_appointments(session.get("idUsuario"))
        return jsonify(payload), status

    def post(self):
        err = RouteHelpers.check_role("paciente", "profesional")
        if err:
            return err
        data = request.get_json() or {}
        created_by_professional = data.get("creado_por_profesional", False)
        metodo_pago = data.get("metodoPago")

        payload, status = appointment_service.create_appointment(
            session["idUsuario"], data,
            created_by_professional=created_by_professional,
        )

        if status == 200 and metodo_pago and session.get("rol") == "paciente":
            id_cita = payload.get("idCita")
            if id_cita:
                professional_id = data.get("idProfesional")
                tipo_cita = data.get("tipoCita", "Consulta")
                desc = f"Consulta psicológica - {tipo_cita}"
                estado_pago = InvoiceService.estado_factura_agendada(metodo_pago)
                invoice_payload, invoice_status = InvoiceService().create_invoice(
                    professional_id,
                    {
                        "idPaciente": session["idUsuario"],
                        "idCita": id_cita,
                        "metodoPago": metodo_pago,
                        "estadoPago": estado_pago,
                        "items": [{"descripcion": desc, "precioUnitario": 100000}],
                    },
                )
                if invoice_payload.get("success"):
                    payload["idFactura"] = invoice_payload.get("idFactura")
                    payload["estadoPagoFactura"] = invoice_payload.get("estadoPago")
                else:
                    payload["facturaGenerada"] = False
                    payload["facturaError"] = invoice_payload.get("message")
                    payload["facturaStatus"] = invoice_status

        return jsonify(payload), status


class CitaDetailResource(MethodView):
    def patch(self, id_cita):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        data = request.get_json() or {}
        payload, status = appointment_service.update_status(
            id_cita, data.get("estado"), session.get("idUsuario"),
        )
        return jsonify(payload), status

    def delete(self, id_cita):
        data = request.get_json() or {}
        motivo = data.get("motivoCancelacion", "").strip()
        user_role = session.get("rol")

        err = RouteHelpers.check_role("paciente", "profesional")
        if err:
            return err

        if user_role == "profesional":
            payload, status = appointment_service.cancel_professional_appointment(
                id_cita, session.get("idUsuario"), motivo,
            )
        else:
            payload, status = appointment_service.cancel_appointment(
                id_cita, session.get("idUsuario"), motivo,
            )
        return jsonify(payload), status


class CitaDisponibleResource(MethodView):
    def get(self):
        tipo = request.args.get("type", "dates" if request.path.endswith("/fechas-disponibles") else "times")
        if tipo == "dates":
            id_profesional = request.args.get("idProfesional")
            anio = request.args.get("anio")
            mes = request.args.get("mes")
            payload, status = appointment_service.get_available_dates(id_profesional, anio, mes)
        else:
            id_profesional = request.args.get("idProfesional")
            fecha = request.args.get("fecha")
            payload, status = appointment_service.get_available_times(id_profesional, fecha)
        return jsonify(payload), status


class CitaProximaResource(MethodView):
    def get(self):
        err = RouteHelpers.check_role("paciente")
        if err:
            return err
        payload, status = appointment_service.get_next_patient_appointment(session.get("idUsuario"))
        return jsonify(payload), status


class CitaHorarioOcupadoResource(MethodView):
    def get(self):
        err = RouteHelpers.check_role("profesional")
        if err:
            return err
        id_profesional = request.args.get("idProfesional")
        fecha = request.args.get("fecha")
        payload, status = appointment_service.get_taken_slots(id_profesional, fecha)
        return jsonify(payload), status


appointment_bp.add_url_rule("/api/citas", view_func=CitaListResource.as_view("citas"))
appointment_bp.add_url_rule("/api/citas/<int:id_cita>", view_func=CitaDetailResource.as_view("cita"))
appointment_bp.add_url_rule("/api/citas/disponibles", view_func=CitaDisponibleResource.as_view("citas_disponibles"))
appointment_bp.add_url_rule("/api/citas/fechas-disponibles", view_func=CitaDisponibleResource.as_view("citas_fechas_disponibles"))
appointment_bp.add_url_rule("/api/citas/proxima", view_func=CitaProximaResource.as_view("cita_proxima"))
appointment_bp.add_url_rule("/api/citas/horarios-ocupados", view_func=CitaHorarioOcupadoResource.as_view("citas_horarios_ocupados"))
appointment_bp.add_url_rule("/api/citas/profesional", view_func=CitaListResource.as_view("citas_profesional"))
appointment_bp.add_url_rule("/api/citas/paciente", view_func=CitaListResource.as_view("citas_paciente"))
