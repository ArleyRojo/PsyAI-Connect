# Migration to add omitidos field to Notificaciones

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0008_alter_citas_estado_alter_disponibilidad_estado'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificaciones',
            name='omitidos',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
