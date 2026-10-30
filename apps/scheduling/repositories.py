import logging
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q, Count, F
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.scheduling.models import Citas, Disponibilidad, Notificaciones
from apps.authentication.models import Register
from apps.billing.models import Facturas

logger = logging.getLogger(__name__)


class AppointmentRepository:
    @staticmethod
    def _format_time(value):
        if value is None:
            return None
        if isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        elif hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        elif isinstance(value, str):
            return value[:5] if len(value) >= 5 else value
        return str(value)

    def appointment_exists(self, professional_id, fecha, hora):
        return Citas.objects.filter(
            idProfesional_id=professional_id,
            fecha=fecha,
            hora=hora,
        ).exclude(estado="Cancelada").exists()

    def get_appointment_in_slot(self, professional_id, fecha, hora):
        try:
            cita = Citas.objects.get(
                idProfesional_id=professional_id,
                fecha=fecha,
                hora=hora,
                estado="Pendiente",
            )
            return {"idCita": cita.idCita, "idPaciente": cita.idPaciente_id}
        except Citas.DoesNotExist:
            try:
                cita = Citas.objects.filter(
                    idProfesional_id=professional_id,
                    fecha=fecha,
                    hora=hora,
                ).exclude(estado="Cancelada").first()
                if cita:
                    return {"idCita": cita.idCita, "idPaciente": cita.idPaciente_id}
            except Exception:
                pass
            return None

    def create_appointment(self, patient_id, professional_id, fecha, hora, tipo_cita, motivo, creado_por_profesional=False):
        with transaction.atomic():
            cita = Citas.objects.create(
                idPaciente_id=patient_id,
                idProfesional_id=professional_id,
                fecha=fecha,
                hora=hora,
                tipoCita=tipo_cita,
                motivo=motivo,
                estado="Pendiente",
                creado_por_profesional=creado_por_profesional,
            )
            return cita.idCita

    def get_daily_availability(self, professional_id, fecha):
        rows = Disponibilidad.objects.filter(
            idProfesional_id=professional_id,
            fecha=fecha,
            estado="Disponible",
        ).values_list("hora_inicio", "hora_fin")
        return [{"hora_inicio": r[0], "hora_fin": r[1]} for r in rows]

    def create_disponibilidad(self, professional_id, fecha, hora_inicio, hora_fin, estado="Disponible"):
        from datetime import date, time as dt_time

        if isinstance(fecha, str):
            fecha = date.fromisoformat(fecha)
        if isinstance(hora_inicio, str):
            hora_inicio = dt_time.fromisoformat(hora_inicio)
        if isinstance(hora_fin, str):
            hora_fin = dt_time.fromisoformat(hora_fin)

        disp = Disponibilidad.objects.create(
            idProfesional_id=professional_id,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            estado=estado,
        )
        return disp.to_dict()

    def get_all_disponibilidad(self, professional_id):
        return list(
            Disponibilidad.objects.filter(
                idProfesional_id=professional_id,
            ).order_by("fecha", "hora_inicio").values_list("idDisponibilidad", "fecha", "hora_inicio", "hora_fin", "estado")
        )

    def get_taken_times(self, professional_id, fecha):
        rows = Citas.objects.filter(
            idProfesional_id=professional_id,
            fecha=fecha,
        ).exclude(estado="Cancelada").values_list("hora", flat=True)
        return [self._format_time(r) for r in rows]

    def get_professional_appointments(self, professional_id, *, pending_only=False, page=1, limit=20):
        offset = (page - 1) * limit
        qs = Citas.objects.filter(
            idProfesional_id=professional_id,
        ).select_related("idPaciente")

        if pending_only:
            qs = qs.filter(estado="Pendiente")
        else:
            qs = qs.exclude(estado="Cancelada").filter(fecha__gte=timezone.localdate())

        qs = qs.order_by("fecha", "hora")[offset : offset + limit]

        result = []
        for cita in qs:
            d = {
                "idCita": cita.idCita,
                "paciente": cita.idPaciente.nombre if cita.idPaciente else None,
                "fotoPerfil": cita.idPaciente.fotoPerfil if cita.idPaciente else None,
                "fecha": cita.fecha,
                "hora": self._format_time(cita.hora),
                "tipoCita": cita.tipoCita,
                "motivo": cita.motivo,
                "estado": cita.estado,
                "creado_por_profesional": cita.creado_por_profesional,
                "idPaciente": cita.idPaciente_id,
            }
            result.append(d)
        return result

    def get_taken_times_by_professional(self, professional_id, fecha):
        rows = Citas.objects.filter(
            idProfesional_id=professional_id,
            fecha=fecha,
        ).exclude(estado="Cancelada").values_list("hora", flat=True)
        return [self._format_time(r) for r in rows]

    def get_next_patient_appointment(self, patient_id):
        try:
            cita = (
                Citas.objects.filter(
                    idPaciente_id=patient_id,
                    estado="Pendiente",
                    fecha__gte=timezone.localdate(),
                )
                .select_related("idProfesional")
                .order_by("fecha", "hora")
                .first()
            )
            if cita:
                return {
                    "fecha": cita.fecha,
                    "hora": self._format_time(cita.hora),
                    "tipoCita": cita.tipoCita,
                    "profesional": cita.idProfesional.nombre if cita.idProfesional else None,
                }
        except Exception:
            pass
        return None

    def get_appointment_owner(self, appointment_id):
        try:
            cita = Citas.objects.get(idCita=appointment_id)
            return (cita.idProfesional_id, cita.idPaciente_id)
        except Citas.DoesNotExist:
            return None

    def get_appointment_full(self, appointment_id):
        try:
            cita = (
                Citas.objects.select_related("idPaciente", "idProfesional")
                .get(idCita=appointment_id)
            )
            return cita
        except Citas.DoesNotExist:
            return None

    def update_appointment_status(self, appointment_id, estado):
        updated = Citas.objects.filter(idCita=appointment_id).update(estado=estado)
        return updated

    def get_patient_appointments(self, patient_id):
        qs = (
            Citas.objects.filter(idPaciente_id=patient_id)
            .select_related("idProfesional")
            .order_by("-fecha", "-hora")
        )

        cita_ids = [c.idCita for c in qs]
        factura_map = {}
        if cita_ids:
            facturas = Facturas.objects.filter(idCita__in=cita_ids, anulada=False).values("idCita", "idFactura", "estadoPago")
            for f in facturas:
                factura_map[f["idCita"]] = {"idFactura": f["idFactura"], "estadoPago": f["estadoPago"]}

        result = []
        for cita in qs:
            factura = factura_map.get(cita.idCita)
            d = {
                "idCita": cita.idCita,
                "fecha": cita.fecha,
                "hora": self._format_time(cita.hora),
                "tipoCita": cita.tipoCita,
                "motivo": cita.motivo,
                "estado": cita.estado,
                "motivoCancelacion": cita.motivoCancelacion,
                "profesional": cita.idProfesional.nombre if cita.idProfesional else None,
                "creado_por_profesional": cita.creado_por_profesional,
                "estadoPago": factura["estadoPago"] if factura else None,
                "idFactura": factura["idFactura"] if factura else None,
            }
            result.append(d)
        return result

    def cancel_patient_appointment(self, appointment_id, patient_id, motivo_cancelacion):
        updated = Citas.objects.filter(
            idCita=appointment_id,
            idPaciente_id=patient_id,
        ).update(estado="Cancelada", motivoCancelacion=motivo_cancelacion)
        return updated

    def cancel_professional_appointment(self, appointment_id, professional_id, motivo_cancelacion):
        updated = Citas.objects.filter(
            idCita=appointment_id,
            idProfesional_id=professional_id,
        ).update(estado="Cancelada", motivoCancelacion=motivo_cancelacion)
        return updated

    def create_notification(self, user_id, rol, titulo, mensaje, tipo="Cita"):
        try:
            Notificaciones.objects.create(
                idUsuario_id=user_id,
                rol=rol,
                titulo=titulo,
                mensaje=mensaje,
                tipo=tipo,
                enviado_por="Sistema",
                estado="enviado",
            )
        except Exception as e:
            logger.error(f"Error creating notification: {e}")

    def get_month_availability(self, professional_id, anio, mes):
        rows = Disponibilidad.objects.filter(
            idProfesional_id=professional_id,
            fecha__year=anio,
            fecha__month=mes,
            estado="Disponible",
        ).values_list("fecha", "hora_inicio", "hora_fin")
        return [{"fecha": r[0], "hora_inicio": r[1], "hora_fin": r[2]} for r in rows]

    def get_month_taken_counts(self, professional_id, anio, mes):
        rows = (
            Citas.objects.filter(
                idProfesional_id=professional_id,
                fecha__year=anio,
                fecha__month=mes,
            )
            .exclude(estado="Cancelada")
            .values("fecha")
            .annotate(ocupadas=Count("idCita"))
        )
        return {row["fecha"].strftime("%Y-%m-%d"): row["ocupadas"] for row in rows}
