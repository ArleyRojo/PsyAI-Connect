from django.core.management import BaseCommand

from apps.authentication.models import Register

VALID_ROLES = {"paciente", "profesional", "admin"}


class Command(BaseCommand):
    help = "Normaliza los roles de los usuarios en BD (strip + lower). Usa --dry-run para ver cambios sin aplicar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo lista los cambios que se harían, sin modificar la BD.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        cambios = []

        for user in Register.objects.all().only("idUsuario", "rol", "email", "nombre"):
            rol_actual = user.rol or ""
            rol_normalizado = rol_actual.strip().lower()
            if rol_actual != rol_normalizado:
                cambios.append(
                    {
                        "id": user.idUsuario,
                        "email": user.email,
                        "nombre": user.nombre,
                        "rol_actual": rol_actual,
                        "rol_nuevo": rol_normalizado,
                    }
                )

        if not cambios:
            self.stdout.write(self.style.SUCCESS("No hay roles que normalizar."))
            return

        self.stdout.write(f"Se encontraron {len(cambios)} rol(es) con formato incorrecto:\n")
        for c in cambios:
            self.stdout.write(
                f"  id={c['id']} email={c['email']} nombre={c['nombre']} "
                f"rol='{c['rol_actual']}' -> '{c['rol_nuevo']}'"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nModo --dry-run: no se aplicaron cambios. Ejecuta sin --dry-run para confirmar."
                )
            )
            return

        confirm = input("\n¿Aplicar cambios? (yes/no): ").strip().lower()
        if confirm != "yes":
            self.stdout.write(self.style.WARNING("Operación cancelada por el usuario."))
            return

        aplicados = 0
        for c in cambios:
            Register.objects.filter(idUsuario=c["id"]).update(rol=c["rol_nuevo"])
            aplicados += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nSe normalizaron {aplicados} rol(es) correctamente.")
        )
