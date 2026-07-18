from django.urls import path
from django.views.decorators.csrf import csrf_exempt

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
        "facturas/<int:id_factura>",
        views.FacturaDetailView.as_view(),
        name="factura_detail",
    ),
    path(
        "facturas/<int:id_factura>/pago",
        views.FacturaPagoView.as_view(),
        name="factura_pago",
    ),
    path(
        "facturas/<int:id_factura>/iniciar-pago",
        views.FacturaPagoView.as_view(),
        name="factura_iniciar_pago",
    ),
    path(
        "facturas/<int:id_factura>/confirmar-pago",
        views.FacturaPagoView.as_view(),
        name="factura_confirmar_pago",
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
        "facturas/emitidas",
        views.FacturaListView.as_view(),
        name="facturas_emitidas",
    ),
    path(
        "facturas/pacientes-profesional",
        views.ProfesionalPacientesView.as_view(),
        name="factura_pacientes",
    ),
    path(
        "webhooks/wompi",
        csrf_exempt(views.WebhookWompiView.as_view()),
        name="webhook_wompi",
    ),
    path(
        "pagos/respuesta",
        views.payment_response_view,
        name="payment_response",
    ),
]
