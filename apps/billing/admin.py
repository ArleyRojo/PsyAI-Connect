from django.contrib import admin

from apps.billing.models import Facturas, ItemsFactura


class ItemsFacturaInline(admin.TabularInline):
    model = ItemsFactura
    extra = 0
    readonly_fields = ("precioUnitario",)


@admin.register(Facturas)
class FacturasAdmin(admin.ModelAdmin):
    list_display = ("idFactura", "idPaciente", "idProfesional", "monto", "estadoPago", "anulada", "fecha")
    list_filter = ("estadoPago", "anulada")
    search_fields = ("idPaciente__email",)
    readonly_fields = ("fecha",)
    inlines = [ItemsFacturaInline]


@admin.register(ItemsFactura)
class ItemsFacturaAdmin(admin.ModelAdmin):
    list_display = ("idItem", "idFactura", "descripcion", "precioUnitario")
