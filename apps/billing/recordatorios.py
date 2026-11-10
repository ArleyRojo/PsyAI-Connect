"""
Recordatorios de cobro (HU-77, CU-56).

Automático (comando `enviar_recordatorios_cobro`, lo ejecuta el programador cada hora):
- Facturas en estado Pendiente y no anuladas.
- Primer aviso a los 3 días de creada la factura; luego uno cada 7 días; máximo 4 avisos.
- Un solo aviso por paciente con el detalle de todas sus facturas que tocan ese día.

Manual: el profesional pulsa "Recordar pago" en una factura suya (máximo una vez cada 24 h).

El aviso siempre queda en la campanita del paciente. Por correo/WhatsApp solo si tiene
activado el tipo "Facturas" en sus preferencias (notificar_paciente con tipo "factura").
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import F, Q
from django.utils import timezone

from apps.billing.models import Facturas

logger = logging.getLogger(__name__)

DIAS_PRIMER_AVISO = 3
DIAS_ENTRE_AVISOS = 7
MAX_AVISOS = 4
HORAS_ENTRE_MANUALES = 24

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _pesos(valor):
    try:
        return "$" + f"{Decimal(valor):,.0f}".replace(",", ".")
    except Exception:
        return "$0"


def _fecha(dt):
    local = timezone.localtime(dt) if timezone.is_aware(dt) else dt
    return f"{local.day} {MESES[local.month - 1]} {local.year}"


def _monto(factura):
    if factura.monto is not None:
        return factura.monto
    return sum((i.precioUnitario or Decimal("0")) for i in factura.items.all())


def facturas_por_recordar(ahora=None):
    """Facturas a las que hoy les toca recordatorio automático."""
    ahora = ahora or timezone.now()
    return (
        Facturas.objects.filter(estadoPago="Pendiente", anulada=False, recordatoriosEnviados__lt=MAX_AVISOS)
        .filter(
            Q(recordatoriosEnviados=0, fecha__lte=ahora - timedelta(days=DIAS_PRIMER_AVISO))
            | Q(recordatoriosEnviados__gt=0, ultimoRecordatorio__lte=ahora - timedelta(days=DIAS_ENTRE_AVISOS))
        )
        .select_related("idPaciente", "idProfesional")
        .prefetch_related("items")
        .order_by("idPaciente_id", "fecha")
    )


def _mensaje(facturas):
    lineas = [
        f"• Factura #{f.idFactura} del {_fecha(f.fecha)} con "
        f"{f.idProfesional.nombre if f.idProfesional_id else 'tu profesional'}: {_pesos(_monto(f))}"
        for f in facturas
    ]
    total = sum(_monto(f) for f in facturas)
    if len(facturas) == 1:
        encabezado = f"Tienes una factura pendiente por {_pesos(total)}."
    else:
        encabezado = f"Tienes {len(facturas)} facturas pendientes por un total de {_pesos(total)}."
    return encabezado + "\n" + "\n".join(lineas) + "\nPuedes verlas y pagarlas en Mis Pagos."


def _avisar(paciente, facturas):
    """Campanita siempre; correo/WhatsApp según preferencias. Devuelve True si salió por algún canal externo."""
    from apps.scheduling.models import Notificaciones

    titulo = "Recordatorio de pago"
    mensaje = _mensaje(facturas)
    Notificaciones.objects.create(
        idUsuario=paciente, rol="paciente", titulo=titulo, mensaje=mensaje, tipo="Factura",
        enviado_por="Sistema", estado="enviado", canal="interno",
    )
    try:
        from apps.core.notifier import notificar_paciente
        return bool(notificar_paciente(paciente, titulo, mensaje, "factura"))
    except Exception as e:  # la campanita ya quedó; el correo no debe romper el proceso
        logger.error("No se pudo enviar el recordatorio de pago a %s: %s", paciente.idUsuario, e)
        return False


def _marcar(facturas, ahora):
    Facturas.objects.filter(idFactura__in=[f.idFactura for f in facturas]).update(
        recordatoriosEnviados=F("recordatoriosEnviados") + 1, ultimoRecordatorio=ahora,
    )


def enviar_automaticos(ahora=None):
    """Envía los recordatorios que tocan. Devuelve (pacientes avisados, facturas recordadas)."""
    ahora = ahora or timezone.now()
    por_paciente = {}
    for factura in facturas_por_recordar(ahora):
        if factura.idPaciente_id:
            por_paciente.setdefault(factura.idPaciente_id, []).append(factura)

    pacientes = facturas_total = 0
    for facturas in por_paciente.values():
        try:
            _avisar(facturas[0].idPaciente, facturas)
            _marcar(facturas, ahora)
            pacientes += 1
            facturas_total += len(facturas)
        except Exception as e:  # se reintenta en la siguiente ejecución
            logger.error("Recordatorio de cobro fallido (paciente %s): %s", facturas[0].idPaciente_id, e)
    return pacientes, facturas_total


def recordar_manual(factura_id, profesional_id):
    """Botón "Recordar pago" del profesional."""
    factura = (
        Facturas.objects.filter(idFactura=factura_id)
        .select_related("idPaciente", "idProfesional").prefetch_related("items").first()
    )
    if not factura:
        return {"success": False, "message": "Factura no encontrada"}, 404
    if factura.idProfesional_id != profesional_id:
        return {"success": False, "message": "No tienes permiso sobre esta factura"}, 403
    if factura.anulada or factura.estadoPago != "Pendiente":
        return {"success": False, "message": "Solo se recuerdan facturas pendientes"}, 400

    ahora = timezone.now()
    if factura.ultimoRecordatorio and ahora - factura.ultimoRecordatorio < timedelta(hours=HORAS_ENTRE_MANUALES):
        return {"success": False, "message": "Ya se envió un recordatorio de esta factura en las últimas 24 horas"}, 429

    externo = _avisar(factura.idPaciente, [factura])
    _marcar([factura], ahora)
    factura.refresh_from_db()
    detalle = "Le llegó a su campanita" + (" y a su correo/WhatsApp." if externo else ".")
    return {
        "success": True,
        "message": f"Recordatorio enviado a {factura.idPaciente.nombre}. {detalle}",
        "recordatoriosEnviados": factura.recordatoriosEnviados,
        "ultimoRecordatorio": factura.ultimoRecordatorio.isoformat(),
    }, 200
