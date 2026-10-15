import os
import json
import shutil
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers import serialize
from django.db import transaction
from apps.billing.models import Facturas, ItemsFactura


class Command(BaseCommand):
    help = "Elimina facturas de prueba (y sus ítems y archivos de evidencia) de forma segura."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirma el borrado real. Sin esta opción es dry-run.",
        )
        parser.add_argument(
            "--force-prod",
            action="store_true",
            help="Permite ejecutar en producción (DEBUG=False).",
        )
        parser.add_argument(
            "--paciente",
            type=str,
            help="Filtrar por nombre o id del paciente.",
        )
        parser.add_argument(
            "--profesional",
            type=str,
            help="Filtrar por nombre o id del profesional.",
        )
        parser.add_argument(
            "--no-backup",
            action="store_true",
            help="Desactiva la creación del backup JSON.",
        )

    def _resolve_user_id(self, value, field_name):
        """value can be numeric id or name (partial). Returns user_id or None."""
        if not value:
            return None
        from apps.authentication.models import Register
        try:
            return int(value)
        except ValueError:
            # buscar por nombre (icontains)
            user = Register.objects.filter(nombre__icontains=value).first()
            if not user:
                raise CommandError(f"No se encontró {field_name} con nombre/id '{value}'")
            return user.idUsuario

    def _build_queryset(self, paciente_id=None, profesional_id=None):
        qs = Facturas.objects.all()
        if paciente_id:
            qs = qs.filter(idPaciente_id=paciente_id)
        if profesional_id:
            qs = qs.filter(idProfesional_id=profesional_id)
        return qs

    def handle(self, *args, **options):
        dry_run = not options["yes"]
        force_prod = options["force_prod"]
        paciente_filter = options["paciente"]
        profesional_filter = options["profesional"]
        make_backup = not options["no_backup"]

        if not settings.DEBUG and not force_prod:
            raise CommandError(
                "Ejecución no permitida en producción (DEBUG=False). Use --force-prod para forzar."
            )

        paciente_id = self._resolve_user_id(paciente_filter, "paciente")
        profesional_id = self._resolve_user_id(profesional_filter, "profesional")

        qs = self._build_queryset(paciente_id, profesional_id)

        total_facturas = qs.count()
        total_items = ItemsFactura.objects.filter(idFactura__in=qs.values_list("idFactura", flat=True)).count()
        evidencia_files = list(qs.exclude(evidencia="").values_list("evidencia", flat=True))

        self.stdout.write(self.style.NOTICE(
            f"Dry-run: {total_facturas} facturas, {total_items} ítems, {len(evidencia_files)} archivos de evidencia."
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se borra nada. Use --yes para confirmar."))
            return

        # Backup
        backup_path = None
        if make_backup:
            backup_dir = os.path.join(settings.BASE_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"billing_{timestamp}.json")
            data = serialize("json", qs.select_related("idPaciente", "idProfesional", "confirmada_por").prefetch_related("items"))
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(data)
            self.stdout.write(self.style.SUCCESS(f"Backup creado en {backup_path}"))

        # Borrado real dentro de transacción
        deleted_facturas = 0
        deleted_items = 0
        deleted_files = 0

        with transaction.atomic():
            for factura in qs.select_for_update():
                # eliminar archivo de evidencia
                if factura.evidencia and factura.evidencia.name:
                    try:
                        # delete file from storage
                        factura.evidencia.delete(save=False)
                        deleted_files += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"No se pudo borrar evidencia de factura {factura.idFactura}: {e}"))
                factura.delete()
                deleted_facturas += 1

        self.stdout.write(self.style.SUCCESS(
            f"Borrado completado: {deleted_facturas} facturas, {deleted_items} ítems (cascada), {deleted_files} archivos de evidencia."
        ))
        if backup_path:
            self.stdout.write(self.style.SUCCESS(f"Backup disponible en {backup_path}"))