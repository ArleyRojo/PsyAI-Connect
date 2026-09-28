# apps/scheduling/management/commands/probar_whatsapp.py
from django.core.management.base import BaseCommand
from apps.core.whatsapp import get_whatsapp_provider

class Command(BaseCommand):
    help = "Envía un WhatsApp de prueba al número indicado (sandbox)"

    def add_arguments(self, parser):
        parser.add_argument("numero", type=str, help="E.164 ej. +573001234567")

    def handle(self, *args, **opts):
        numero = opts["numero"]
        prov = get_whatsapp_provider()
        sid = prov.enviar_whatsapp(numero, texto="✅ Prueba desde PsyAI Connect")
        self.stdout.write(self.style.SUCCESS(f"Enviado (sid={sid})"))