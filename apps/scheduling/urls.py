from django.urls import path

from apps.scheduling.views import (
    CitaListResource,
    CitaDetailResource,
    CitaDisponibleResource,
    CitaProximaResource,
    CitaHorarioOcupadoResource,
)

app_name = "scheduling"

urlpatterns = [
    path("citas", CitaListResource.as_view(), name="citas"),
    path("citas/<int:id_cita>", CitaDetailResource.as_view(), name="cita"),
    path("citas/disponibles", CitaDisponibleResource.as_view(), name="citas_disponibles"),
    path("citas/fechas-disponibles", CitaDisponibleResource.as_view(), name="citas_fechas_disponibles"),
    path("citas/proxima", CitaProximaResource.as_view(), name="cita_proxima"),
    path("citas/horarios-ocupados", CitaHorarioOcupadoResource.as_view(), name="citas_horarios_ocupados"),
    path("citas/profesional", CitaListResource.as_view(), name="citas_profesional"),
    path("citas/paciente", CitaListResource.as_view(), name="citas_paciente"),
]
