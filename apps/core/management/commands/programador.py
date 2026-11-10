"""
Programador de tareas automáticas (lo usa el servicio `scheduler` de Docker).

Corre sin parar y ejecuta:
- cada 5 minutos: recordatorios de cita (24 h antes), notificaciones programadas del admin
  y la copia de seguridad del día cuando llega la hora configurada (HU-30)
- cada hora: recordatorios de cobro de facturas pendientes (HU-77)
Además deja una "señal de vida" para que el admin vea en Mantenimiento que está funcionando.

Uso: python manage.py programador          (sigue corriendo)
     python manage.py programador --una-vez (ejecuta todo una vez y termina; útil para probar)
"""
import logging
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import close_old_connections

logger = logging.getLogger(__name__)

TAREAS = [
    # (comando y argumentos, cada cuántos segundos)
    (("enviar_recordatorios",), 5 * 60),
    (("enviar_notificaciones_programadas",), 5 * 60),
    (("copia_seguridad", "--automatica"), 5 * 60),
    (("enviar_recordatorios_cobro",), 60 * 60),
]


class Command(BaseCommand):
    help = "Ejecuta las tareas automáticas (recordatorios y notificaciones) cada cierto tiempo"

    def add_arguments(self, parser):
        parser.add_argument("--una-vez", action="store_true", help="Ejecuta todas las tareas una vez y termina")

    def ejecutar(self, comando, cerrar_conexiones=True):
        # En el modo continuo se renuevan las conexiones para no dejar una abierta horas
        if cerrar_conexiones:
            close_old_connections()
        try:
            call_command(*comando, stdout=self.stdout)
        except Exception as e:  # una tarea con error no detiene a las demás
            logger.exception("Error en la tarea %s: %s", comando[0], e)
            self.stderr.write(f"Error en {comando[0]}: {e}")
        finally:
            if cerrar_conexiones:
                close_old_connections()

    def latido(self):
        """Señal de vida que se ve en Mantenimiento > Estado del sistema."""
        try:
            close_old_connections()
            from apps.admin_panel.mantenimiento import registrar_latido
            registrar_latido()
        except Exception as e:
            logger.warning("No se pudo registrar la señal del programador: %s", e)

    def handle(self, *args, **options):
        if options["una_vez"]:
            from apps.admin_panel.mantenimiento import registrar_latido
            registrar_latido()
            for comando, _ in TAREAS:
                self.ejecutar(comando, cerrar_conexiones=False)
            return

        self.stdout.write(self.style.SUCCESS("Programador iniciado"))
        ultima = {comando: 0.0 for comando, _ in TAREAS}
        while True:
            self.latido()
            ahora = time.monotonic()
            for comando, cada in TAREAS:
                if not ultima[comando] or ahora - ultima[comando] >= cada:
                    ultima[comando] = ahora
                    self.ejecutar(comando)
            time.sleep(30)
