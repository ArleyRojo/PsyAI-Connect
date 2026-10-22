from django.urls import path

from apps.billing import views

app_name = "billing"

urlpatterns = [
    path(
        "facturas",
        views.FacturaListView.as_view(),
        name="factura_list",
    ),
    path(
        "facturas/mias",
        views.FacturaListView.as_view(),
        name="factura_list_mias",
    ),
    path(
        "facturas/emitidas",
        views.FacturaListView.as_view(),
        name="facturas_emitidas",
    ),
    path(
        "facturas/<int:id_factura>",
        views.FacturaDetailView.as_view(),
        name="factura_detail",
    ),
    path(
        "facturas/stats",
        views.FacturaStatsView.as_view(),
        name="factura_stats",
    ),
    path(
        "facturas/estadisticas-admin",
        views.FacturaStatsView.as_view(),
        name="factura_estadisticas_admin",
    ),
    path(
        "facturas/<int:id_factura>/evidencia",
        views.FacturaEvidenciaView.as_view(),
        name="factura_evidencia",
    ),
    path(
        "facturas/<int:id_factura>/confirmar-pago",
        views.FacturaConfirmarPagoView.as_view(),
        name="factura_confirmar_pago",
    ),
    path(
        "facturas/pacientes-profesional",
        views.ProfesionalPacientesView.as_view(),
        name="factura_pacientes",
    ),
]