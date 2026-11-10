"""Recordatorios automáticos de facturas pendientes (HU-77). Lo ejecuta el programador cada hora."""
from django.core.management.base import BaseCommand

from apps.billing.recordatorios import enviar_automaticos


class Command(BaseCommand):
    help = "Envía recordatorios de facturas Pendientes (a los 3 días y luego cada 7, máximo 4)"

    def handle(self, *args, **options):
        pacientes, facturas = enviar_automaticos()
        self.stdout.write(self.style.SUCCESS(
            f"Recordatorios de cobro: {pacientes} paciente(s) avisados, {facturas} factura(s) recordadas"
        ))
