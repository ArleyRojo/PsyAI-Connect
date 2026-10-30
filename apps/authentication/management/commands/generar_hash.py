from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password


class Command(BaseCommand):
    help = "Genera un hash Argon2id para una contraseña, listo para insertar en MySQL."

    def add_arguments(self, parser):
        parser.add_argument("contrasena", type=str, help="Contraseña en texto plano a hashear")

    def handle(self, *args, **options):
        contrasena = options["contrasena"]
        hash_argon2 = make_password(contrasena)
        self.stdout.write(self.style.SUCCESS(f"Hash Argon2id generado: {hash_argon2}"))
        self.stdout.write(
            self.style.WARNING(
                "Ejemplo de uso en MySQL:\n"
                f"INSERT INTO Register (nombre, email, contrasena, rol, estadoCuenta, activo, email_verificado)\n"
                f"VALUES ('Nombre', 'email@correo.com', '{hash_argon2}', 'paciente', 'Activa', 1, 1);"
            )
        )
