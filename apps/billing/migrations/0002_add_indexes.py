from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="facturas",
            index=models.Index(
                fields=["idPaciente", "fecha"],
                name="idx_facturas_pac_fecha",
            ),
        ),
        migrations.AddIndex(
            model_name="facturas",
            index=models.Index(
                fields=["idProfesional", "fecha"],
                name="idx_facturas_prof_fecha",
            ),
        ),
        migrations.AddIndex(
            model_name="facturas",
            index=models.Index(
                fields=["estadoPago", "anulada"],
                name="idx_facturas_estado",
            ),
        ),
    ]
