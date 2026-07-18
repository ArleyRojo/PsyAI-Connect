from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0001_initial"),
    ]

    operations = [
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
