# apps/scheduling/management/commands/enviar_recordatorios.py
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.scheduling.models import Citas
from apps.core.notifier import notificar_paciente

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Envía recordatorios de cita 24 h antes (idempotente)"

    def handle(self, *args, **opts):
        ahora = timezone.now()
        ventana_inicio = ahora + timedelta(hours=23, minutes=55)
        ventana_fin = ahora + timedelta(hours=24, minutes=5)

        # Use range-based filter to avoid MySQL CONVERT_TZ issues with __date
        fecha_start = ventana_inicio.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_end = fecha_start + timedelta(days=1)

        citas = Citas.objects.filter(
            fecha__gte=fecha_start,
            fecha__lt=fecha_end,
            hora__range=(ventana_inicio.time(), ventana_fin.time()),
            estado__in=["Pendiente","Confirmada"],
            recordatorio_enviado=False,
        ).select_related("idPaciente")

        for cita in citas:
            for intento in range(3):
                try:
                    ok = notificar_paciente(
                        cita.idPaciente,
                        "Recordatorio de cita",
                        f"Tu cita es mañana a las {cita.hora.strftime('%H:%M')}"
                        f" en {cita.lugar or 'la sede habitual'}.",
                        "recordatorio_cita",
                    )
                    if ok:
                        cita.recordatorio_enviado = True
                        cita.save(update_fields=["recordatorio_enviado"])
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