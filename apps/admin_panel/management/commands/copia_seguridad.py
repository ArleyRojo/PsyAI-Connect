"""Copia de seguridad cifrada de la base de datos (HU-30).

python manage.py copia_seguridad              -> crea una copia manual ya
python manage.py copia_seguridad --automatica -> crea la copia del día solo si ya es la hora configurada
"""
from django.core.management.base import BaseCommand

from apps.admin_panel import mantenimiento


class Command(BaseCommand):
    help = "Crea una copia de seguridad cifrada de la base de datos"

    def add_arguments(self, parser):
        parser.add_argument("--automatica", action="store_true",
                            help="Solo crea la copia del día si ya pasó la hora configurada")

    def handle(self, *args, **options):
        if options["automatica"]:
            self.stdout.write(mantenimiento.copia_automatica_si_toca())
            return
        payload, status = mantenimiento.crear_copia("Consola", "manual")
        self.stdout.write(payload["message"] + (f": {payload['copia']['archivo']}" if status == 201 else ""))
