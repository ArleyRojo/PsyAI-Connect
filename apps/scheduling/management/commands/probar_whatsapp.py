# apps/scheduling/management/commands/probar_whatsapp.py
from django.core.management.base import BaseCommand
from apps.core.notifier import enviar_prueba

class Command(BaseCommand):
    help = "Envía un WhatsApp de prueba al número indicado y muestra resultado real"

    def add_arguments(self, parser):
        parser.add_argument("numero", type=str, help="E.164 ej. +573001234567")

    def handle(self, *args, **opts):
        numero = opts["numero"]
        ok, msg = enviar_prueba(numero)
        if ok:
            self.stdout.write(self.style.SUCCESS(f"OK – {msg}"))
        else:
            self.stderr.write(self.style.ERROR(f"FAIL – {msg}"))