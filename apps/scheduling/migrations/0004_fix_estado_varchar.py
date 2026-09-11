from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0003_add_confirmada_estado'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE Citas MODIFY estado VARCHAR(20) DEFAULT 'Pendiente'",
            ],
            reverse_sql=[
                "ALTER TABLE Citas MODIFY estado ENUM('Pendiente','Completada','Cancelada') DEFAULT 'Pendiente'",
            ],
        ),
        migrations.RunSQL(
            sql=[
                "ALTER TABLE Citas ADD INDEX idx_citas_prof_fecha (idProfesional, fecha)",
                "ALTER TABLE Citas ADD INDEX idx_citas_pac_fecha (idPaciente, fecha)",
                "ALTER TABLE Citas ADD INDEX idx_citas_fecha_estado (fecha, estado)",
                "ALTER TABLE Disponibilidad ADD INDEX idx_disponibilidad_prof_fecha (idProfesional, fecha)",
            ],
            reverse_sql=[
                "ALTER TABLE Citas DROP INDEX idx_citas_prof_fecha",
                "ALTER TABLE Citas DROP INDEX idx_citas_pac_fecha",
                "ALTER TABLE Citas DROP INDEX idx_citas_fecha_estado",
                "ALTER TABLE Disponibilidad DROP INDEX idx_disponibilidad_prof_fecha",
            ],
        ),
    ]
