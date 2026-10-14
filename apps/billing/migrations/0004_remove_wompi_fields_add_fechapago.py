# Generated migration: remove Wompi fields, add fechaPago, simplify estadoPago
# RunPython to migrate Parcial/Cancelado -> Pendiente

from django.db import migrations, models


def migrate_estado_pago(apps, schema_editor):
    Facturas = apps.get_model('billing', 'Facturas')
    # Parcial and Cancelado become Pendiente
    Facturas.objects.filter(estadoPago__in=['Parcial', 'Cancelado']).update(estadoPago='Pendiente')


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_remove_facturas_idx_facturas_estado_and_more'),
    ]

    operations = [
        # Drop the index that references the columns we will drop
        migrations.RemoveIndex(
            model_name='facturas',
            name='idx_facturas_referencia',
        ),
        # Data migration
        migrations.RunPython(migrate_estado_pago, migrations.RunPython.noop),

        # Remove old fields
        migrations.RemoveField(
            model_name='facturas',
            name='metodoPago',
        ),
        migrations.RemoveField(
            model_name='facturas',
            name='referenciaPago',
        ),
        migrations.RemoveField(
            model_name='facturas',
            name='idTransaccionPago',
        ),

        # Add new field
        migrations.AddField(
            model_name='facturas',
            name='fechaPago',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # Alter estadoPago choices
        migrations.AlterField(
            model_name='facturas',
            name='estadoPago',
            field=models.CharField(
                choices=[('Pendiente', 'Pendiente'), ('Pagado', 'Pagado')],
                default='Pendiente',
                max_length=10,
            ),
        ),
    ]