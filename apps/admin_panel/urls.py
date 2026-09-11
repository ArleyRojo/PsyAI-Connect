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
        "admin/chatbot-historial",
        views.AdminChatbotHistorialAPIView.as_view(),
        name="admin_chatbot_historial",
    ),
]
