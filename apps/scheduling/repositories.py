import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.scheduling.models import CalificacionCita, Citas, Disponibilidad, Notificaciones
from apps.billing.models import Facturas

logger = logging.getLogger(__name__)


class AppointmentRepository:
    def save_appointment(self, appointment, fields=None):
        appointment.save(update_fields=fields) if fields else appointment.save()
        return appointment

    def save_notification(self, notification, fields):
        notification.save(update_fields=fields)
        return notification

    def update_notification_status_by_provider_id(self, provider_msg_id, status):
        return Notificaciones.objects.filter(providerMsgId=provider_msg_id).update(estado=status)

    def get_future_appointment_counts_by_pair(self, active_states, day):
        return list(
            Citas.objects.filter(estado__in=active_states, fecha__gte=day)
            .values("idPaciente_id", "idProfesional_id").annotate(n=Count("idCita"))
        )

    def cancel_future_appointments_for_reassignment(self, patient_id, professional_id, new_name, active_states, day):
        return Citas.objects.filter(
            estado__in=active_states, fecha__gte=day,
            idPaciente_id=patient_id, idProfesional_id=professional_id,
        ).update(estado="Cancelada", motivoCancelacion=f"Caso reasignado a {new_name}")
    def delete_old_notifications(self, cutoff):
        return Notificaciones.objects.filter(fecha__lt=cutoff).exclude(estado="pendiente").delete()

    def get_appointment_counts_by_day(self, start_date, end_date):
        return list(
            Citas.objects.filter(fecha__gte=start_date, fecha__lte=end_date)
            .exclude(estado="Cancelada").values("fecha")
            .annotate(total=Count("pk"))
        )

    def count_appointments_for_day(self, day):
        return Citas.objects.filter(fecha=day).exclude(estado="Cancelada").count()
    def notification_exists(self, user_id, role, kind, title, message):
        return Notificaciones.objects.filter(
            idUsuario_id=user_id, rol=role, tipo=kind, titulo=title, mensaje=message
        ).exists()

    def get_appointment_by_id_or_none(self, appointment_id):
        return Citas.objects.filter(idCita=appointment_id).first()

    def get_patient_notifications(self, user_id):
        notifications = Notificaciones.objects.filter(
            idUsuario_id=user_id, rol="paciente", canal="interno"
        ).order_by("-fecha", "-idNotificacion")
        recent = notifications[:30]
        return {
            "no_leidas": notifications.filter(leido=False).count(),
            "notificaciones": [
                {
                    "idNotificacion": item.idNotificacion,
                    "titulo": item.titulo or "Notificación",
                    "mensaje": item.mensaje or "",
                    "fecha": item.fecha.isoformat() if item.fecha else None,
                    "leido": bool(item.leido),
                }
                for item in recent
            ],
        }

    def mark_patient_notifications_read(self, user_id):
        return Notificaciones.objects.filter(
            idUsuario_id=user_id, rol="paciente", canal="interno", leido=False
        ).update(leido=True)

    def get_appointment_for_update(self, appointment_id):
        return Citas.objects.select_for_update().get(idCita=appointment_id)

    def get_scheduled_admin_notifications(self, now):
        return Notificaciones.objects.filter(
            estado="pendiente", enviado_por="Admin", fecha_programada__lte=now
        ).order_by("fecha_programada")

    def get_appointments_for_reminder(self, window):
        return Citas.objects.filter(
            window,
            estado__in=["Pendiente", "Confirmada"],
            recordatorio_enviado=False,
        ).select_related("idPaciente")

    def get_appointments_in_reminder_window(self, start, end):
        if start.date() == end.date():
            window = Q(fecha=start.date(), hora__range=(start.time(), end.time()))
        else:
            window = (
                Q(fecha=start.date(), hora__gte=start.time())
                | Q(fecha=end.date(), hora__lte=end.time())
            )
        return self.get_appointments_for_reminder(window)

    def mark_reminder_sent(self, appointment_id):
        return Citas.objects.filter(idCita=appointment_id).update(recordatorio_enviado=True)

    def create_notification_attempt(self, **data):
        return Notificaciones.objects.create(**data)

    def get_notification_by_provider_id(self, provider_msg_id):
        return Notificaciones.objects.filter(providerMsgId=provider_msg_id).first()

    def save_provider_notification_status(self, notification, status):
        notification.estado = status
        notification.save(update_fields=["estado"])
        return notification

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
            # Próximas citas + las Confirmadas que ya pasaron y siguen sin completar
            qs = qs.exclude(estado="Cancelada").filter(
                Q(fecha__gte=timezone.localdate()) | Q(estado="Confirmada")
            )

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
                # Se decide con la hora del servidor (Colombia), no con el reloj del PC
                "puedeCompletar": self.cita_ya_empezo(cita),
            }
            result.append(d)
        return result

    @staticmethod
    def cita_ya_empezo(cita):
        """True si la cita está Confirmada y ya llegó su hora de inicio."""
        if cita.estado != "Confirmada" or not cita.fecha or not cita.hora:
            return False
        return timezone.make_aware(datetime.combine(cita.fecha, cita.hora)) <= timezone.now()

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

        calificacion_map = {}
        if cita_ids:
            for cal in CalificacionCita.objects.filter(idCita_id__in=cita_ids):
                calificacion_map[cal.idCita_id] = {"puntuacion": cal.puntuacion, "comentario": cal.comentario}

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
                "calificacion": calificacion_map.get(cita.idCita),
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

    # ── Calificaciones de citas (HU-67) ───────────────────────────────────

    def get_cita_del_paciente(self, cita_id, patient_id):
        return Citas.objects.filter(idCita=cita_id, idPaciente_id=patient_id).first()

    def guardar_calificacion(self, cita, puntuacion, comentario):
        calificacion, creada = CalificacionCita.objects.update_or_create(
            idCita=cita, defaults={"puntuacion": puntuacion, "comentario": comentario}
        )
        return calificacion, creada

    def resumen_calificaciones(self, professional_id):
        datos = CalificacionCita.objects.filter(idCita__idProfesional_id=professional_id).aggregate(
            promedio=Avg("puntuacion"), total=Count("idCalificacion")
        )
        promedio = round(float(datos["promedio"]), 1) if datos["promedio"] is not None else None
        return promedio, datos["total"]

    def calificaciones_del_profesional(self, professional_id):
        """Sin datos del paciente: las calificaciones son anónimas para el profesional."""
        return [
            c.to_dict()
            for c in CalificacionCita.objects.filter(idCita__idProfesional_id=professional_id)
        ]

    def resumen_por_profesional(self):
        """{idProfesional: (promedio, total)} para mostrar en la lista pública de profesionales."""
        filas = (
            CalificacionCita.objects.values("idCita__idProfesional_id")
            .annotate(promedio=Avg("puntuacion"), total=Count("idCalificacion"))
        )
        return {
            f["idCita__idProfesional_id"]: (round(float(f["promedio"]), 1), f["total"])
            for f in filas
        }
