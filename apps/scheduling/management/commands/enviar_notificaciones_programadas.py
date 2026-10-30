import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.admin_panel.repositories import AdminRepository
from apps.scheduling.models import Notificaciones

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Envía notificaciones programadas pendientes (fecha_programada <= now) creadas por Admin"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra qué notificaciones se enviarían sin enviarlas realmente",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()
        
        # Buscar notificaciones pendientes de admin con fecha_programada <= now
        notificaciones = Notificaciones.objects.filter(
            estado="pendiente",
            enviado_por="Admin",
            fecha_programada__lte=now,
        ).order_by("fecha_programada")
        
        count = notificaciones.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No hay notificaciones programadas para enviar"))
            return
        
        self.stdout.write(f"Encontradas {count} notificación(es) programada(s) para enviar")
        
        repo = AdminRepository()
        total_enviados = 0
        total_fallidos = 0
        
        for notif in notificaciones:
            self.stdout.write(f"  Procesando #{notif.idNotificacion}: {notif.titulo} -> {notif.destinatario}")
            
            if dry_run:
                self.stdout.write(f"    [DRY RUN] Se enviaría a {notif.destinatario}")
                continue
            
            try:
                enviados, fallidos, error_detalle = repo._send_admin_notification_emails(
                    notificacion_id=notif.idNotificacion,
                    destinatario=notif.destinatario,
                    email_individual=notif.email_individual,
                    titulo=notif.titulo,
                    mensaje=notif.mensaje,
                    tipo=notif.tipo,
                )
                
                if enviados > 0:
                    notif.estado = "enviado"
                    notif.errorDetalle = None
                    total_enviados += 1
                    self.stdout.write(self.style.SUCCESS(f"    Enviada a {enviados} destinatario(s)"))
                else:
                    notif.estado = "fallido"
                    notif.errorDetalle = error_detalle or "No se pudo enviar a ningún destinatario"
                    total_fallidos += 1
                    self.stdout.write(self.style.ERROR(f"    Fallida: {notif.errorDetalle}"))
                
                notif.save(update_fields=["estado", "errorDetalle"])
                
            except Exception as e:
                notif.estado = "fallido"
                notif.errorDetalle = str(e)
                notif.save(update_fields=["estado", "errorDetalle"])
                total_fallidos += 1
                self.stdout.write(self.style.ERROR(f"    Error: {e}"))
                logger.exception("Error enviando notificación programada #%d", notif.idNotificacion)
        
        self.stdout.write(self.style.SUCCESS(
            f"\nResumen: {total_enviados} enviada(s), {total_fallidos} fallida(s)"
        ))