"""Utilidades para generación de códigos QR de pago."""

from io import BytesIO

import qrcode
from django.core.files.base import ContentFile


FACTURAS_URL = "http://127.0.0.1:8000/aside-patient/facturas.html"


def build_qr_payload(mensaje_texto: str | None, facturas_url: str = FACTURAS_URL) -> str:
    """Construye el texto que se codifica dentro del código QR.

    Incluye los datos bancarios del profesional y el enlace a facturas para
    que el paciente pueda escanear y completar el pago.
    """
    lines = []
    if mensaje_texto:
        lines.append(mensaje_texto.strip())
    lines.append("")
    lines.append("Pagar en: " + facturas_url)
    return "\n".join(lines)


def generate_qr_png(data: str) -> ContentFile:
    """Genera una imagen PNG de código QR a partir de un texto.

    Devuelve un ``ContentFile`` listo para guardar en un ``ImageField``.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return ContentFile(buffer.read(), name="payment_qr.png")
