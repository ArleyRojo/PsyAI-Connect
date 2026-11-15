# apps/scheduling/management/commands/enviar_recordatorios.py
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.scheduling.repositories import AppointmentRepository
from apps.core.notifier import notificar_paciente

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Envía recordatorios de cita 24 h antes (idempotente)"

    def handle(self, *args, **opts):
        # La fecha y la hora de las citas están en hora de Colombia, por eso se usa
        # la hora local (con timezone.now() la ventana quedaba corrida 5 horas).
        ahora = timezone.localtime()
        ventana_inicio = ahora + timedelta(hours=23, minutes=55)
        ventana_fin = ahora + timedelta(hours=24, minutes=5)

        repo = AppointmentRepository()
        citas = repo.get_appointments_in_reminder_window(ventana_inicio, ventana_fin)

        for cita in citas:
            for intento in range(3):
                try:
                    ok = notificar_paciente(
                        cita.idPaciente,
                        "Recordatorio de cita",
                        f"Tu cita es mañana a las {cita.hora.strftime('%H:%M')}"
                        f" en {getattr(cita, 'lugar', None) or 'la sede habitual'}.",
                        "recordatorio_cita",
                    )
                    if ok:
                        repo.mark_reminder_sent(cita.idCita)
                        logger.info("Recordatorio enviado cita %s", cita.idCita)
                        break
                    else:
                        logger.warning("Recordatorio no enviado (sin canal) cita %s", cita.idCita)
                        break
                except Exception as e:
                    logger.warning("Intento %d fallido cita %s: %s", intento+1, cita.idCita, e)
                    if intento == 2:
                        logger.error("Recordatorio fallido definitivamente cita %s", cita.idCita)
        self.stdout.write(self.style.SUCCESS("Proceso de recordatorios finalizado"))
