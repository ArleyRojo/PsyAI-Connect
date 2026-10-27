from datetime import date
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.authentication.models import Register
from apps.patients.models import PerfilPaciente


class Command(BaseCommand):
    help = 'Lista usuarios menores de la edad mínima de registro (EDAD_MINIMA_REGISTRO)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--edad-minima',
            type=int,
            default=None,
            help='Edad mínima para considerar menor (por defecto usa EDAD_MINIMA_REGISTRO de settings)',
        )
        parser.add_argument(
            '--incluir-activos',
            action='store_true',
            help='Incluir usuarios activos (por defecto solo muestra activos)',
        )
        parser.add_argument(
            '--exportar-csv',
            type=str,
            help='Ruta de archivo CSV para exportar los resultados',
        )

    def handle(self, *args, **options):
        edad_minima = options['edad_minima'] or getattr(settings, 'EDAD_MINIMA_REGISTRO', 18)
        incluir_activos = options['incluir_activos']
        exportar_csv = options.get('exportar_csv')

        self.stdout.write(f"Buscando usuarios menores de {edad_minima} años...")

        # Obtener todos los usuarios con fecha_nacimiento en su perfil
        usuarios_con_fecha = Register.objects.select_related('perfil_paciente').filter(
            perfil_paciente__fecha_nacimiento__isnull=False
        )

        if not incluir_activos:
            usuarios_con_fecha = usuarios_con_fecha.filter(activo=True, estadoCuenta='Activa')

        menores = []
        for usuario in usuarios_con_fecha:
            perfil = usuario.perfil_paciente
            if perfil and perfil.fecha_nacimiento:
                hoy = date.today()
                fecha_nac = perfil.fecha_nacimiento
                edad = date.today().year - fecha_nac.year
                if (date.today().month, date.today().day) < (fecha_nac.month, fecha_nac.day):
                    edad -= 1
                if edad < edad_minima:
                    menores.append({
                        'idUsuario': usuario.idUsuario,
                        'email': usuario.email,
                        'nombre': usuario.nombre,
                        'fecha_nacimiento': perfil.fecha_nacimiento,
                        'edad': edad,
                        'activo': usuario.activo,
                        'estadoCuenta': usuario.estadoCuenta,
                        'rol': usuario.rol,
                    })

        if not menores:
            self.stdout.write(self.style.SUCCESS('No se encontraron usuarios menores de la edad mínima.'))
            return

        self.stdout.write(f"\nEncontrados {len(menores)} usuarios menores de {edad_minima} años:\n")
        self.stdout.write(f"{'ID':<6} {'Email':<30} {'Nombre':<20} {'Fecha Nac.':<12} {'Edad':<4} {'Activo':<6} {'Estado':<10} {'Rol':<12}")
        self.stdout.write("-" * 120)
        for m in menores:
            self.stdout.write(
                f"{m['idUsuario']:<6} {m['email']:<30} {m['nombre']:<20} "
                f"{m['fecha_nacimiento']} {m['edad']:<4} "
                f"{str(m['activo']):<6} {m['estadoCuenta']:<10} {m['rol']:<12}"
            )

        if exportar_csv:
            import csv
            with open(exportar_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['idUsuario', 'email', 'nombre', 'fecha_nacimiento', 'edad', 'activo', 'estadoCuenta', 'rol'])
                for m in menores:
                    writer.writerow([
                        m['idUsuario'], m['email'], m['nombre'],
                        m['fecha_nacimiento'], m['edad'],
                        m['activo'], m['estadoCuenta'], m['rol']
                    ])
            self.stdout.write(self.style.SUCCESS(f"\nResultados exportados a {exportar_csv}"))

        self.stdout.write(
            self.style.WARNING(
                f"\n⚠️  Estos usuarios son menores de {edad_minima} años. "
                "Según la legislación colombiana (Ley 1098 de 2006), requieren "
                "autorización de su representante legal para el tratamiento de datos."
            )
        )