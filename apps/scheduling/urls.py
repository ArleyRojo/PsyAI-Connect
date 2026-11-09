from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.scheduling.views import (
    CitaViewSet,
    CitaDetailViewSet,
    CitaDisponibleResource,
    CitaProximaResource,
    CitaHorarioOcupadoResource,
    PatientNotificationsResource,
    CalificacionCitaResource,
    CalificacionesProfesionalResource,
)

app_name = "scheduling"

router = DefaultRouter()
router.register(r"citas", CitaViewSet, basename="cita")

urlpatterns = [
    path("citas", CitaViewSet.as_view({"post": "create"}), name="citas_crear"),
    path("citas/<int:pk>", CitaDetailViewSet.as_view({"patch": "partial_update", "delete": "destroy"}), name="cita"),
    path("citas/<int:pk>/calificacion", CalificacionCitaResource.as_view(), name="cita_calificacion"),
    path("profesional/calificaciones", CalificacionesProfesionalResource.as_view(), name="profesional_calificaciones"),
    path("citas/disponibles", CitaDisponibleResource.as_view(), name="citas_disponibles"),
    path("citas/fechas-disponibles", CitaDisponibleResource.as_view(), name="citas_fechas_disponibles"),
    path("citas/proxima", CitaProximaResource.as_view(), name="cita_proxima"),
    # Alias con tilde para compatibilidad con frontend
    path("citas/próxima", CitaProximaResource.as_view(), name="cita_proxima_tilde"),
    path("citas/horarios-ocupados", CitaHorarioOcupadoResource.as_view(), name="citas_horarios_ocupados"),
    path("paciente/notificaciones", PatientNotificationsResource.as_view(), name="paciente_notificaciones"),
    path("citas/profesional", CitaViewSet.as_view({"get": "list"}), name="citas_profesional"),
    path("citas/paciente", CitaViewSet.as_view({"get": "list"}), name="citas_paciente"),
    path("", include(router.urls)),
]
