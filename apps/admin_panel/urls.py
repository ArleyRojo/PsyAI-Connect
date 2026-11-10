from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.admin_panel import views

app_name = "admin_panel"

router = DefaultRouter(trailing_slash=False)
router.register(r"admin/usuarios", views.AdminUsuarioViewSet, basename="admin-usuarios")
router.register(r"admin/chatbot-config", views.AdminChatbotConfigViewSet, basename="admin-chatbot-config")

urlpatterns = [
    path(
        "admin/chatbot-config/palabras-detectadas",
        views.AdminChatbotPalabrasAPIView.as_view(),
        name="admin_chatbot_palabras",
    ),
    path("", include(router.urls)),
    path(
        "admin/crear-columnas-diagnostico",
        views.AdminDiagnosticoAPIView.as_view(),
        name="admin_diagnostico",
    ),
    path(
        "admin/stats",
        views.AdminStatsAPIView.as_view(),
        name="admin_stats",
    ),
    path(
        "admin/stats/stream",
        views.AdminStatsStreamAPIView.as_view(),
        name="admin_stats_stream",
    ),
    path(
        "admin/logs/stream",
        views.AdminLogsStreamAPIView.as_view(),
        name="admin_logs_stream",
    ),
    path(
        "admin/roles/usuarios",
        views.AdminRolAPIView.as_view(),
        name="admin_roles_usuarios",
    ),
    path(
        "admin/roles/historial",
        views.AdminRolAPIView.as_view(),
        name="admin_roles_historial",
    ),
    path(
        "admin/notificaciones",
        views.AdminNotificacionAPIView.as_view(),
        name="admin_notificaciones",
    ),
    path(
        "admin/notificaciones/<int:id_notificacion>",
        views.AdminNotificacionAPIView.as_view(),
        name="admin_notificacion",
    ),
    path(
        "admin/logs",
        views.AdminLogAPIView.as_view(),
        name="admin_logs",
    ),
    path(
        "admin/online",
        views.AdminOnlineAPIView.as_view(),
        name="admin_online",
    ),
    path(
        "admin/seguridad",
        views.AdminSeguridadAPIView.as_view(),
        name="admin_seguridad",
    ),
    path(
        "admin/asignaciones",
        views.AdminAsignacionesAPIView.as_view(),
        name="admin_asignaciones",
    ),
    path(
        "admin/asignaciones/reasignar",
        views.AdminReasignarAPIView.as_view(),
        name="admin_asignaciones_reasignar",
    ),
    path(
        "admin/asignaciones/historial",
        views.AdminHistorialAsignacionesAPIView.as_view(),
        name="admin_asignaciones_historial",
    ),
    path(
        "admin/seguridad/revisar",
        views.AdminRevisarPoliticasAPIView.as_view(),
        name="admin_seguridad_revisar",
    ),
    path(
        "politicas/contrasena",
        views.PoliticaContrasenaAPIView.as_view(),
        name="politica_contrasena",
    ),
    path("admin/roles/catalogo", views.AdminCatalogoRolesAPIView.as_view(), name="admin_roles_catalogo"),
    path("admin/roles/catalogo/<int:id_rol>", views.AdminCatalogoRolesAPIView.as_view(), name="admin_rol_catalogo"),
    path("admin/mantenimiento", views.AdminMantenimientoEstadoAPIView.as_view(), name="admin_mantenimiento"),
    path("admin/mantenimiento/accion", views.AdminMantenimientoAccionAPIView.as_view(),
         name="admin_mantenimiento_accion"),
    path("admin/mantenimiento/modo", views.AdminMantenimientoModoAPIView.as_view(), name="admin_mantenimiento_modo"),
    path("admin/copias", views.AdminCopiasAPIView.as_view(), name="admin_copias"),
    path("admin/copias/hora", views.AdminCopiasHoraAPIView.as_view(), name="admin_copias_hora"),
    path("admin/copias/restaurar", views.AdminCopiasRestaurarAPIView.as_view(), name="admin_copias_restaurar"),
    path(
        "sesion/inactividad",
        views.SesionInactividadAPIView.as_view(),
        name="sesion_inactividad",
    ),
    path(
        "admin/chatbot-historial",
        views.AdminChatbotHistorialAPIView.as_view(),
        name="admin_chatbot_historial",
    ),
]
