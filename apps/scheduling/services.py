import logging
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone as tz
from apps.core.notifier import notificar_paciente
from apps.scheduling.repositories import AppointmentRepository
from apps.scheduling.models import Citas
from apps.billing.repositories import InvoiceRepository

logger = logging.getLogger(__name__)

VALID_CITAS_ESTADOS = {"Pendiente", "Confirmada", "Completada", "Cancelada"}


class AppointmentMailService:
    @staticmethod
    def _get_site_url():
        return getattr(settings, "SITE_URL", "http://localhost:8000")

    @staticmethod
    def _formatear_fecha(fecha):
        if hasattr(fecha, "strftime"):
            meses = [
                "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
            ]
            dias = ["Lunes", "Martes", "MiÃ©rcoles", "Jueves", "Viernes", "SÃ¡bado", "Domingo"]
            return f"{dias[fecha.weekday()]} {fecha.day} de {meses[fecha.month]} de {fecha.year}"
        return str(fecha)

    @staticmethod
    def _formatear_hora(hora):
        if hora is None:
            return ""
        if isinstance(hora, timedelta):
            total_seconds = int(hora.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        if hasattr(hora, "strftime"):
            return hora.strftime("%H:%M")
        return str(hora)

    @classmethod
    def send_cita_notificacion(cls, recipient_email, titulo, mensaje, *, nombre_contraparte=None,
                               contraparte_label="Contacto", fecha=None, hora=None, tipo_cita=None,
                               motivo=None, estado=None, motivo_cancelacion=None, cta_link=None,
                               cta_texto=None, recipient_user_id=None):
        if not recipient_email:
            logger.warning("No se enviÃ³ correo de cita: destinatario vacÃ­o")
            return

        if recipient_user_id:
            try:
                from apps.patients.models import PerfilPaciente
                perfil = PerfilPaciente.objects.filter(idPaciente=recipient_user_id).first()
                if perfil and perfil.prefNotificaciones == "Desactivadas":
                    logger.info(f"Correo omitido (notificaciones desactivadas): {recipient_email}")
                    return
            except Exception:
                pass
        if not recipient_email:
            logger.warning("No se enviÃ³ correo de cita: destinatario vacÃ­o")
            return

        site_url = cls._get_site_url()
        ctx = {
            "titulo": titulo,
            "mensaje": mensaje,
            "nombre_contraparte": nombre_contraparte,
            "contraparte_label": contraparte_label,
            "fecha": cls._formatear_fecha(fecha) if fecha else "",
            "hora": cls._formatear_hora(hora) if hora else "",
            "tipo_cita": tipo_cita,
            "motivo": motivo,
            "estado": estado,
            "motivo_cancelacion": motivo_cancelacion,
            "cta_link": cta_link,
            "cta_texto": cta_texto or "Ver cita",
            "site_url": site_url,
        }

        try:
            subject = titulo
            text_body = f"{titulo}\n\n{mensaje}\n\nFecha: {ctx['fecha']}\nHora: {ctx['hora']}"
            html_body = render_to_string("emails/cita_notificacion.html", ctx)

            from django.core.mail import EmailMultiAlternatives
            msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [recipient_email])
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=True)
            logger.info(f"Correo enviado a {recipient_email}: {titulo}")
        except Exception as e:
            logger.error(f"Error enviando correo a {recipient_email}: {e}")


class AppointmentService:
    def __init__(self):
        self.repo = AppointmentRepository()

    @staticmethod
    def _notify(paciente, tipo, **ctx):
        textos = {
            "recordatorio_cita": ("Recordatorio de cita",
                "Tu cita es maÃ±ana a las {hora}. DirecciÃ³n: {lugar}."),
            "confirmacion_cita": ("Cita confirmada",
                "Tu cita del {fecha} a las {hora} ha sido confirmada."),
            "cancelacion_cita": ("Cita cancelada",
                "La cita del {fecha} a las {hora} ha sido cancelada."),
            "mensaje_profesional": ("Nuevo mensaje",
                "Tienes un mensaje de tu profesional. Ingresa a la plataforma."),
        }
        tit, plantilla = textos[tipo]
        mensaje = plantilla.format(**ctx)
        notificar_paciente(paciente, tit, mensaje, tipo)

    def create_appointment(self, patient_id, data, *, created_by_professional=False):
        professional_id = data.get("idProfesional")
        fecha = data.get("fecha")
        hora = data.get("hora")
        if isinstance(hora, str) and "-" in hora:
            hora = hora.split("-")[0]
        motivo = data.get("motivo", "")
        tipo_cita = data.get("tipoCita")

        if not professional_id or not fecha or not hora:
            return {"success": False, "message": "Datos incompletos"}, 400

        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            hora_obj = datetime.strptime(hora, "%H:%M").time() if isinstance(hora, str) else hora
            fecha_hora_cita = tz.make_aware(datetime.combine(fecha_obj, hora_obj))
            if fecha_hora_cita < tz.now():
                return {"success": False, "message": "No se pueden agendar citas en el pasado"}, 400
        except (ValueError, TypeError):
            pass

        if created_by_professional:
            target_patient_id = data.get("idPaciente")
            if not target_patient_id:
                return {"success": False, "message": "El campo idPaciente es requerido"}, 400
        else:
            target_patient_id = patient_id
            if not target_patient_id:
                return {"success": False, "message": "SesiÃ³n de usuario invÃ¡lida"}, 401

        existing = self.repo.get_appointment_in_slot(professional_id, fecha, hora)
        if existing:
            if existing["idPaciente"] == target_patient_id:
                self.repo.cancel_patient_appointment(
                    existing["idCita"], target_patient_id,
                    "Reemplazada por nuevo intento de agendamiento"
                )
            else:
                msg = "Ese horario ya estÃ¡ ocupado" if created_by_professional else "Horario no disponible"
                return {"success": False, "message": msg}, 409

        try:
            cita_id = self.repo.create_appointment(
                target_patient_id, professional_id, fecha, hora, tipo_cita, motivo,
                created_by_professional if created_by_professional else False,
            )
            # Toda cita empieza pendiente; la confirma la contraparte correspondiente.
            self.repo.update_appointment_status(cita_id, "Pendiente")
        except IntegrityError:
            msg = "Ese horario ya estÃ¡ ocupado" if created_by_professional else "Horario no disponible"
            return {"success": False, "message": msg}, 409

        try:
            cita = self.repo.get_appointment_full(cita_id)
            if cita:
                site_url = AppointmentMailService._get_site_url()
                prof = cita.idProfesional
                pac = cita.idPaciente
                if created_by_professional:
                    # Crear la cita no equivale a confirmarla ni facturarla.
                    AppointmentMailService.send_cita_notificacion(
                        recipient_email=pac.email,
                        titulo="Nueva cita pendiente de confirmacion",
                        mensaje=f"Tu profesional {prof.nombre if prof else ''} programo una cita. Esta pendiente de confirmacion.",
                        nombre_contraparte=prof.nombre if prof else None,
                        contraparte_label="Profesional",
                        fecha=cita.fecha, hora=cita.hora,
                        tipo_cita=cita.tipoCita, motivo=cita.motivo,
                        estado=cita.estado,
                        cta_link=f"{site_url}/aside-patient/agenda-quotes.html",
                        recipient_user_id=pac.idUsuario if pac else None,
                    )
                else:
                    # Notificar al profesional de nueva solicitud
                    AppointmentMailService.send_cita_notificacion(
                        recipient_email=prof.email if prof else None,
                        titulo="Nueva solicitud de cita",
                        mensaje=f"El paciente {pac.nombre if pac else ''} ha solicitado una cita contigo.",
                        nombre_contraparte=pac.nombre if pac else None,
                        contraparte_label="Paciente",
                        fecha=cita.fecha, hora=cita.hora,
                        tipo_cita=cita.tipoCita, motivo=cita.motivo,
                        estado=cita.estado,
                        cta_link=f"{site_url}/aside-professional/my.agenda.html",
                    )
                    # Notificar al paciente que la solicitud fue enviada
                    AppointmentMailService.send_cita_notificacion(
                        recipient_email=pac.email if pac else None,
                        titulo="Solicitud de cita enviada",
                        mensaje=f"Tu solicitud de cita con {prof.nombre if prof else 'tu profesional'} ha sido enviada. Queda pendiente de confirmaciÃ³n.",
                        nombre_contraparte=prof.nombre if prof else None,
                        contraparte_label="Profesional",
                        fecha=cita.fecha, hora=cita.hora,
                        tipo_cita=cita.tipoCita, motivo=cita.motivo,
                        estado=cita.estado,
                        cta_link=f"{site_url}/aside-patient/agenda-quotes.html",
                        recipient_user_id=pac.idUsuario if pac else None,
                    )
                    # No enviar notificaciÃ³n centralizada de confirmaciÃ³n aquÃ­
        except Exception as e:
            logger.error(f"Error enviando correo de nueva cita: {e}")

        return {"success": True, "message": "Cita agendada correctamente", "idCita": cita_id}, 200

    def get_available_times(self, professional_id, fecha):
        if not professional_id or not fecha:
            return {"success": False, "message": "Datos incompletos"}, 400

        disponibilidades = self.repo.get_daily_availability(professional_id, fecha)
        if not disponibilidades:
            return {"success": True, "horarios": []}, 200

        ocupadas = self.repo.get_taken_times(professional_id, fecha)
        horarios_set = set()

        for disponibilidad in disponibilidades:
            inicio = disponibilidad["hora_inicio"]
            fin = disponibilidad["hora_fin"]
            if isinstance(inicio, timedelta):
                inicio = (datetime.min + inicio).time()
            if isinstance(fin, timedelta):
                fin = (datetime.min + fin).time()

            hora_actual = inicio
            while hora_actual < fin:
                h_str = hora_actual.strftime("%H:%M")
                if h_str not in ocupadas:
                    horarios_set.add(h_str)
                hora_actual = (datetime.combine(date.today(), hora_actual) + timedelta(minutes=60)).time()

        horarios_ordenados = sorted(list(horarios_set))
        return {"success": True, "horarios": horarios_ordenados}, 200

    def list_professional_appointments(self, professional_id, *, pending_only=False, page=1, limit=20):
        citas = self.repo.get_professional_appointments(
            professional_id, pending_only=pending_only, page=page, limit=limit,
        )
        for cita in citas:
            if cita.get("fecha"):
                cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y") if hasattr(cita["fecha"], "strftime") else str(cita["fecha"])
            if cita.get("hora"):
                cita["hora"] = str(cita["hora"])
            if cita.get("fotoPerfil"):
                cita["foto_perfil"] = cita["fotoPerfil"]
        return {"success": True, "citas": citas}, 200

    def get_taken_slots(self, professional_id, fecha):
        if not professional_id or not fecha:
            return {"success": False, "message": "Datos incompletos"}, 400
        return {
            "success": True,
            "horarios_ocupados": self.repo.get_taken_times_by_professional(professional_id, fecha),
        }, 200

    def get_next_patient_appointment(self, patient_id):
        cita = self.repo.get_next_patient_appointment(patient_id)
        if not cita:
            return {"success": True, "cita": None}, 200
        cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y") if hasattr(cita["fecha"], "strftime") else str(cita["fecha"])
        cita["hora"] = str(cita["hora"])
        return {"success": True, "cita": cita}, 200

    def update_status(self, appointment_id, estado, acting_user_id, acting_role="profesional", extra_data=None):
        if not appointment_id or not estado:
            return {"success": False, "message": "Datos incompletos"}, 400

        if estado not in VALID_CITAS_ESTADOS:
            return {"success": False, "message": f"Estado invÃ¡lido. Opciones: {', '.join(VALID_CITAS_ESTADOS)}"}, 400

        row = self.repo.get_appointment_owner(appointment_id)
        if not row:
            return {"success": False, "message": "Cita no encontrada"}, 404

        # Validaciones de transiciÃ³n
        cita_obj = self.repo.get_appointment_full(appointment_id)
        if not cita_obj:
            return {"success": False, "message": "Cita no encontrada"}, 404
        if acting_role == "profesional":
            if row[0] != acting_user_id:
                return {"success": False, "message": "No tienes permiso"}, 403
            if estado == "Confirmada" and cita_obj.creado_por_profesional:
                return {"success": False, "message": "Esta cita debe ser confirmada por el paciente"}, 403
        elif acting_role == "paciente":
            if row[1] != acting_user_id or (estado == "Confirmada" and not cita_obj.creado_por_profesional):
                return {"success": False, "message": "No tienes permiso para confirmar esta cita"}, 403
        else:
            return {"success": False, "message": "No autorizado"}, 403
        if cita_obj.estado == "Cancelada":
            return {"success": False, "message": "No se puede cambiar estado de una cita cancelada"}, 400
        # No permitir confirmar citas pasadas
        from django.utils import timezone as tz
        if estado == "Confirmada":
            cita_dt = tz.make_aware(datetime.combine(cita_obj.fecha, cita_obj.hora))
            if cita_dt < tz.now():
                return {"success": False, "message": "No se puede confirmar una cita pasada"}, 400

        # Actualizar estado dentro de transacciÃ³n para crear factura atÃ³micamente
        from django.db import transaction
        from apps.billing.models import Facturas
        from apps.billing.repositories import InvoiceRepository
        from decimal import Decimal, InvalidOperation

        with transaction.atomic():
            # Bloquear fila de cita
            from apps.scheduling.models import Citas
            cita_locked = Citas.objects.select_for_update().get(idCita=appointment_id)

            # Si se confirma, crear factura si no existe
            if estado == "Confirmada":
                if not Facturas.objects.filter(idCita=appointment_id, anulada=False).exists():
                    monto = None
                    descripcion = f"Cita {cita_locked.tipoCita}"
                    if extra_data:
                        monto_raw = extra_data.get("monto")
                        if monto_raw is not None:
                            try:
                                monto = Decimal(str(monto_raw))
                            except (InvalidOperation, ValueError):
                                return {"success": False, "message": "Monto inválido"}, 400
                        desc_extra = extra_data.get("descripcion")
                        if desc_extra:
                            descripcion = desc_extra
                    if monto is None:
                        monto = Decimal(str(getattr(settings, "CITA_MONTO_DEFAULT", "100000")))
                    if monto <= 0:
                        return {"success": False, "message": "El monto debe ser mayor a 0"}, 400

                    invoice_repo = InvoiceRepository()
                    items = [{"descripcion": descripcion, "precioUnitario": str(monto)}]
                    invoice_repo.create_invoice(
                        patient_id=cita_locked.idPaciente_id,
                        professional_id=cita_locked.idProfesional_id,
                        cita_id=appointment_id,
                        items=items,
                        estadoPago="Pendiente",
                    )
            cita_locked.estado = estado
            cita_locked.save(update_fields=["estado"])

        # Notificaciones (fuera de transacciÃ³n)
        try:
            cita = self.repo.get_appointment_full(appointment_id)
            if cita:
                site_url = AppointmentMailService._get_site_url()
                pac = cita.idPaciente
                prof = cita.idProfesional
                AppointmentMailService.send_cita_notificacion(
                    recipient_email=pac.email if pac else None,
                    titulo=f"Cita actualizada: {estado}",
                    mensaje=f"Tu cita ha sido actualizada a estado \"{estado}\".",
                    nombre_contraparte=prof.nombre if prof else None,
                    contraparte_label="Profesional",
                    fecha=cita.fecha, hora=cita.hora,
                    tipo_cita=cita.tipoCita, motivo=cita.motivo,
                    estado=estado,
                    cta_link=f"{site_url}/aside-patient/agenda-quotes.html",
                    recipient_user_id=pac.idUsuario if pac else None,
                )
                if estado == "Confirmada":
                    self._notify(pac, "confirmacion_cita",
                                 fecha=cita.fecha.strftime("%d/%m/%Y"),
                                 hora=cita.hora.strftime("%H:%M"),
                                 lugar=getattr(cita, "lugar", None) or "Por definir")
                    if acting_role == "paciente":
                        AppointmentMailService.send_cita_notificacion(
                            recipient_email=prof.email if prof else None,
                            titulo="Cita aceptada por el paciente",
                            mensaje=f"{pac.nombre if pac else 'El paciente'} confirmÃ³ la cita que agendaste.",
                            nombre_contraparte=pac.nombre if pac else None,
                            contraparte_label="Paciente",
                            fecha=cita.fecha, hora=cita.hora,
                            tipo_cita=cita.tipoCita, motivo=cita.motivo,
                            estado=estado,
                            cta_link=f"{site_url}/aside-professional/my.agenda.html",
                        )
                elif estado == "Cancelada":
                    self._notify(pac, "cancelacion_cita",
                                 fecha=cita.fecha.strftime("%d/%m/%Y"),
                                 hora=cita.hora.strftime("%H:%M"),
                                 lugar=getattr(cita, "lugar", None) or "Por definir")
        except Exception as e:
            logger.error(f"Error enviando correo de actualizaciÃ³n de estado: {e}")

        return {"success": True, "message": f"Cita {estado}"}, 200

    def list_patient_appointments(self, patient_id):
        citas = self.repo.get_patient_appointments(patient_id)
        for cita in citas:
            if cita.get("fecha"):
                cita["fecha"] = cita["fecha"].strftime("%d/%m/%Y") if hasattr(cita["fecha"], "strftime") else str(cita["fecha"])
            if cita.get("hora"):
                cita["hora"] = str(cita["hora"])
        return {"success": True, "citas": citas}, 200

    def cancel_appointment(self, appointment_id, patient_id, motivo_cancelacion):
        if not motivo_cancelacion or not motivo_cancelacion.strip():
            return {"success": False, "message": "Debes indicar el motivo de la cancelaciÃ³n"}, 400

        row = self.repo.get_appointment_owner(appointment_id)
        if not row:
            return {"success": False, "message": "Cita no encontrada"}, 404

        professional_id = row[0]
        rowcount = self.repo.cancel_patient_appointment(appointment_id, patient_id, motivo_cancelacion.strip())
        if rowcount == 0:
            return {"success": False, "message": "Cita no encontrada o ya cancelada"}, 404

        if professional_id:
            self.repo.create_notification(
                user_id=professional_id, rol="profesional",
                titulo="Cita cancelada por paciente",
                mensaje=f"El paciente ha cancelado su cita. Motivo: {motivo_cancelacion.strip()}",
                tipo="Alerta",
            )

        try:
            cita = self.repo.get_appointment_full(appointment_id)
            if cita:
                site_url = AppointmentMailService._get_site_url()
                prof = cita.idProfesional
                pac = cita.idPaciente
                AppointmentMailService.send_cita_notificacion(
                    recipient_email=prof.email if prof else None,
                    titulo="Cita cancelada por paciente",
                    mensaje=f"El paciente {pac.nombre if pac else ''} ha cancelado la cita.",
                    nombre_contraparte=pac.nombre if pac else None,
                    contraparte_label="Paciente",
                    fecha=cita.fecha, hora=cita.hora,
                    tipo_cita=cita.tipoCita, motivo=cita.motivo,
                    estado="Cancelada",
                    motivo_cancelacion=motivo_cancelacion.strip(),
                    cta_link=f"{site_url}/aside-professional/my.agenda.html",
                )
                AppointmentMailService.send_cita_notificacion(
                    recipient_email=pac.email if pac else None,
                    titulo="Cita cancelada",
                    mensaje=f"Has cancelado tu cita con {prof.nombre if prof else 'tu profesional'}.",
                    nombre_contraparte=prof.nombre if prof else None,
                    contraparte_label="Profesional",
                    fecha=cita.fecha, hora=cita.hora,
                    tipo_cita=cita.tipoCita, motivo=cita.motivo,
                    estado="Cancelada",
                    motivo_cancelacion=motivo_cancelacion.strip(),
                    cta_link=f"{site_url}/aside-patient/agenda-quotes.html",
                    recipient_user_id=pac.idUsuario if pac else None,
                )
                # notificaciÃ³n centralizada
                self._notify(pac, "cancelacion_cita",
                             fecha=cita.fecha.strftime("%d/%m/%Y"),
                             hora=cita.hora.strftime("%H:%M"),
                             lugar=getattr(cita, "lugar", None) or "Por definir")
        except Exception as e:
            logger.error(f"Error enviando correo de cancelaciÃ³n (paciente): {e}")

        return {"success": True, "message": "Cita cancelada correctamente"}, 200

    def cancel_professional_appointment(self, appointment_id, professional_id, motivo_cancelacion):
        if not motivo_cancelacion or not motivo_cancelacion.strip():
            return {"success": False, "message": "Debes indicar el motivo de la cancelaciÃ³n"}, 400

        row = self.repo.get_appointment_owner(appointment_id)
        if not row:
            return {"success": False, "message": "Cita no encontrada"}, 404
        if row[0] != professional_id:
            return {"success": False, "message": "No tienes permiso para cancelar esta cita"}, 403

        rowcount = self.repo.cancel_professional_appointment(
            appointment_id, professional_id, motivo_cancelacion.strip()
        )
        if rowcount == 0:
            return {"success": False, "message": "No se pudo cancelar la cita"}, 400

        patient_id = row[1] if len(row) > 1 else None
        if patient_id:
            self.repo.create_notification(
                user_id=patient_id, rol="paciente",
                titulo="Cita cancelada",
                mensaje=f"El profesional ha cancelado tu cita. Motivo: {motivo_cancelacion.strip()}",
                tipo="Alerta",
            )

        try:
            cita = self.repo.get_appointment_full(appointment_id)
            if cita:
                site_url = AppointmentMailService._get_site_url()
                prof = cita.idProfesional
                pac = cita.idPaciente
                AppointmentMailService.send_cita_notificacion(
                    recipient_email=pac.email if pac else None,
                    titulo="Cita cancelada por el profesional",
                    mensaje=f"El profesional {prof.nombre if prof else ''} ha cancelado tu cita.",
                    nombre_contraparte=prof.nombre if prof else None,
                    contraparte_label="Profesional",
                    fecha=cita.fecha, hora=cita.hora,
                    tipo_cita=cita.tipoCita, motivo=cita.motivo,
                    estado="Cancelada",
                    motivo_cancelacion=motivo_cancelacion.strip(),
                    cta_link=f"{site_url}/aside-patient/agenda-quotes.html",
                    recipient_user_id=pac.idUsuario if pac else None,
                )
                # notificaciÃ³n centralizada
                self._notify(pac, "cancelacion_cita",
                             fecha=cita.fecha.strftime("%d/%m/%Y"),
                             hora=cita.hora.strftime("%H:%M"),
                             lugar=getattr(cita, "lugar", None) or "Por definir")
        except Exception as e:
            logger.error(f"Error enviando correo de cancelaciÃ³n (profesional): {e}")

        return {"success": True, "message": "Cita cancelada correctamente"}, 200

    def get_available_dates(self, professional_id, anio, mes):
        if not professional_id or not anio or not mes:
            return {"success": False, "message": "Datos incompletos"}, 400

        try:
            anio = int(anio)
            mes = int(mes)
        except (ValueError, TypeError):
            return {"success": False, "message": "AÃ±o o mes invÃ¡lido"}, 400

        disponibilidades = self.repo.get_month_availability(professional_id, anio, mes)
        if not disponibilidades:
            return {"success": True, "fechas": []}, 200

        slots_por_fecha = {}
        for disponibilidad in disponibilidades:
            fecha_obj = disponibilidad["fecha"]
            fecha_str = fecha_obj.strftime("%Y-%m-%d") if hasattr(fecha_obj, "strftime") else str(fecha_obj)
            inicio = disponibilidad["hora_inicio"]
            fin = disponibilidad["hora_fin"]
            if isinstance(inicio, timedelta):
                inicio = (datetime.min + inicio).time()
            if isinstance(fin, timedelta):
                fin = (datetime.min + fin).time()
            slots_por_fecha.setdefault(fecha_str, 0)
            hora_actual = inicio
            while hora_actual < fin:
                slots_por_fecha[fecha_str] += 1
                hora_actual = (datetime.combine(date.today(), hora_actual) + timedelta(minutes=60)).time()

        ocupadas_por_fecha = self.repo.get_month_taken_counts(professional_id, anio, mes)
        fechas = [
            fecha_key
            for fecha_key, total_slots in slots_por_fecha.items()
            if ocupadas_por_fecha.get(fecha_key, 0) < total_slots
        ]
        return {"success": True, "fechas": sorted(fechas)}, 200

class DisponibilidadService:
    def __init__(self):
        self.repo = AppointmentRepository()

    def create_availability(self, professional_id, data):
        fecha = data.get("fecha")
        hora_inicio = data.get("horaInicio") or data.get("hora_inicio")
        hora_fin = data.get("horaFin") or data.get("hora_fin")

        if not all([fecha, hora_inicio, hora_fin]):
            return {"success": False, "message": "Datos incompletos (fecha, horaInicio, horaFin)"}, 400

        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            if fecha_obj < tz.localdate():
                return {"success": False, "message": "No se puede crear disponibilidad en el pasado"}, 400
        except (ValueError, TypeError):
            pass

        try:
            disp = self.repo.create_disponibilidad(
                professional_id, fecha, hora_inicio, hora_fin,
            )
            return {"success": True, "message": "Disponibilidad creada", "disponibilidad": disp}, 201
        except Exception as e:
            logger.error(f"Error creating disponibilidad: {e}")
            return {"success": False, "message": "Error al crear disponibilidad"}, 500

    def get_availability(self, professional_id):
        rows = self.repo.get_all_disponibilidad(professional_id)
        disponibilidad = [
            {
                "idDisponibilidad": r[0],
                "fecha": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
                "hora_inicio": r[2].strftime("%H:%M") if hasattr(r[2], "strftime") else str(r[2]),
                "hora_fin": r[3].strftime("%H:%M") if hasattr(r[3], "strftime") else str(r[3]),
                "estado": r[4],
            }
            for r in rows
        ]
        return {"success": True, "disponibilidad": disponibilidad}, 200
