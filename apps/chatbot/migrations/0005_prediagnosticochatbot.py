import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0004_chatbotconfig_off_topic_response'),
        ('authentication', '0001_initial'),  # ajusta al nombre real de tu primera migración de authentication si es distinto
    ]

    operations = [
        migrations.CreateModel(
            name='PrediagnosticoChatbot',
            fields=[
                ('idPrediagnostico', models.AutoField(primary_key=True, serialize=False)),
                ('resumenPaciente', models.TextField()),
                ('resumenProfesional', models.TextField()),
                ('posiblesAreas', models.JSONField(default=list)),
                ('recomendaciones', models.JSONField(default=list)),
                ('nivelRiesgo', models.CharField(choices=[('bajo', 'Bajo'), ('moderado', 'Moderado'), ('alto', 'Alto'), ('critico', 'Crítico')], default='bajo', max_length=20)),
                ('requiereAtencionUrgente', models.BooleanField(default=False)),
                ('profesionalNotificado', models.BooleanField(default=False)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('idPaciente', models.ForeignKey(db_column='idPaciente', on_delete=django.db.models.deletion.CASCADE, to='authentication.register')),
            ],
            options={'db_table': 'PrediagnosticoChatbot'},
        ),
    ]