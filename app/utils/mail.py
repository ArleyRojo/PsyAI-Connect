import os
import logging
import json
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


def send_recovery_email(recipient_email, recovery_link):
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("SMTP_FROM", "onboarding@resend.dev")

    if not api_key:
        logger.warning("Resend no configurado. Falta RESEND_API_KEY.")
        return False

    body_html = f"""
    <html>
    <body style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; padding: 20px; background-color: #f0f5fc;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; padding: 32px; border: 1.5px solid #D6E8FA;">
            <h2 style="color: #0D47A1; font-family: 'Lora', Georgia, serif;">Recuperaci\u00f3n de contrase\u00f1a</h2>
            <p style="color: #0D1F3C; font-size: 16px;">Has solicitado recuperar tu contrase\u00f1a en PsyAI Connect.</p>
            <p style="color: #0D1F3C; font-size: 16px;">Haz clic en el siguiente enlace para crear una nueva contrase\u00f1a:</p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{recovery_link}" style="background-color: #0D47A1; color: white; padding: 14px 28px; text-decoration: none; border-radius: 10px; font-weight: bold; display: inline-block;">Restablecer contrase\u00f1a</a>
            </div>
            <p style="color: #7B92AC; font-size: 14px;">Este enlace expirar\u00e1 en 1 hora.</p>
            <p style="color: #7B92AC; font-size: 14px;">Si no solicitaste este cambio, puedes ignorar este correo en forma segura.</p>
        </div>
    </body>
    </html>
    """

    payload = {
        "from": sender,
        "to": [recipient_email],
        "subject": "Recuperaci\u00f3n de contrase\u00f1a \u2014 PsyAI Connect",
        "html": body_html,
    }

    try:
        req = urlrequest.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=15) as resp:
            status_code = resp.getcode()
            response_text = resp.read().decode("utf-8", errors="ignore")

        if status_code in (200, 201):
            logger.info(f"Correo de recuperaci\u00f3n enviado a {recipient_email}")
            return True

        print(f"[RESEND ERROR] Status {status_code}: {response_text}", flush=True)
        return False
    except HTTPError as e:
        response_text = e.read().decode("utf-8", errors="ignore")
        print(f"[RESEND ERROR] HTTP {e.code}: {response_text}", flush=True)
        return False
    except (URLError, TimeoutError, OSError) as e:
        print(f"[RESEND ERROR] {e}", flush=True)
        return False
