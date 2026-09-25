from django.db import migrations, models


def fix_estado_column(apps, schema_editor):
    if schema_editor.connection.vendor == "mysql":
        schema_editor.execute(
            "ALTER TABLE Citas MODIFY estado VARCHAR(20) DEFAULT 'Pendiente'"
        )


def reverse_fix_estado_column(apps, schema_editor):
    if schema_editor.connection.vendor == "mysql":
        schema_editor.execute(
            "ALTER TABLE Citas MODIFY estado ENUM('Pendiente','Completada','Cancelada') DEFAULT 'Pendiente'"
        )


class Migration(migrations.Migration):

    # MySQL no puede hacer rollback de DDL: sin esto, Django bloquea el ALTER TABLE
    # ejecutado dentro de RunPython (TransactionManagementError).
    atomic = False

    dependencies = [
        ('scheduling', '0003_add_confirmada_estado'),
    ]

    operations = [
        migrations.RunPython(fix_estado_column, reverse_fix_estado_column),
        migrations.AddIndex(
            model_name="citas",
            index=models.Index(
                fields=["idProfesional", "fecha"],
                name="idx_citas_prof_fecha",
            ),
        ),
        migrations.AddIndex(
            model_name="citas",
            index=models.Index(
                fields=["idPaciente", "fecha"],
                name="idx_citas_pac_fecha",
            ),
        ),
        migrations.AddIndex(
            model_name="citas",
            index=models.Index(
                fields=["fecha", "estado"],
                name="idx_citas_fecha_estado",
            ),
        ),
        migrations.AddIndex(
            model_name="disponibilidad",
            index=models.Index(
                fields=["idProfesional", "fecha"],
                name="idx_disponibilidad_prof_fecha",
            ),
        ),
    ]