from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.scheduling.views import (
    CitaViewSet,
    CitaDetailViewSet,
    CitaDisponibleResource,
    CitaProximaResource,
    CitaHorarioOcupadoResource,
)

app_name = "scheduling"

router = DefaultRouter()
router.register(r"citas", CitaViewSet, basename="cita")

urlpatterns = [
    path("citas", CitaViewSet.as_view({"post": "create"}), name="citas_crear"),
    path("citas/<int:pk>", CitaDetailViewSet.as_view({"patch": "partial_update", "delete": "destroy"}), name="cita"),
    path("citas/disponibles", CitaDisponibleResource.as_view(), name="citas_disponibles"),
    path("citas/fechas-disponibles", CitaDisponibleResource.as_view(), name="citas_fechas_disponibles"),
    path("citas/proxima", CitaProximaResource.as_view(), name="cita_proxima"),
    path("citas/horarios-ocupados", CitaHorarioOcupadoResource.as_view(), name="citas_horarios_ocupados"),
    path("citas/profesional", CitaViewSet.as_view({"get": "list"}), name="citas_profesional"),
    path("citas/paciente", CitaViewSet.as_view({"get": "list"}), name="citas_paciente"),
    path("", include(router.urls)),
]
