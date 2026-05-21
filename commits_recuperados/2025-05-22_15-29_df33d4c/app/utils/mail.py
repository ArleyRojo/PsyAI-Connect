import os
import smtplib
from flask import current_app
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_recovery_email(recipient_email, recovery_link):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_password]):
        current_app.logger.warning("SMTP no configurado. No se pudo enviar el correo de recuperación.")
        return

    subject = "Recuperación de contraseña - PsyAI Connect"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Recuperación de contraseña</h2>
        <p>Has solicitado recuperar tu contraseña en PsyAI Connect.</p>
        <p>Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
        <p><a href="{recovery_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Restablecer contraseña</a></p>
        <p>Este enlace expirará en 1 hora.</p>
        <p>Si no solicitaste este cambio, puedes ignorar este correo.</p>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = recipient_email
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, recipient_email, msg.as_string())

        current_app.logger.info(f"Recovery email sent to {recipient_email}")
    except Exception as e:
        current_app.logger.error(f"Failed to send recovery email: {e}")
