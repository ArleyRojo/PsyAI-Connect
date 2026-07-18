from django.db import migrations
from django.utils import timezone


def fix_naive_datetimes(apps, schema_editor):
    EvolucionPaciente = apps.get_model("patients", "EvolucionPaciente")
    for evo in EvolucionPaciente.objects.filter(fecha__isnull=False):
        if evo.fecha.tzinfo is None:
            aware = timezone.make_aware(evo.fecha, timezone.get_current_timezone())
            EvolucionPaciente.objects.filter(pk=evo.pk).update(fecha=aware)


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(fix_naive_datetimes, migrations.RunPython.noop),
    ]
