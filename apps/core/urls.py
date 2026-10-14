from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = "core"

urlpatterns = [
    path("healthz/", csrf_exempt(views.health_check), name="healthz"),
    path("notificaciones/probar/", csrf_exempt(views.notificacion_prueba), name="notificacion-prueba"),
    path("config/pago/", views.config_pago, name="config-pago"),
]
