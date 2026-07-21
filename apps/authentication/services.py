import logging
import os
import re
import secrets
from datetime import datetime, timedelta

from django.conf import settings as dj_settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.authentication.repositories import AuthRepository, SecurityRepository
from apps.authentication.security import SecurityHelper

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(message)


class Validator:
    @staticmethod
    def required(value, field_name):
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"El campo '{field_name}' es requerido", field_name)
        return value

    @staticmethod
    def email(value, field_name="email"):
        if not value:
            raise ValidationError(f"El campo '{field_name}' es requerido", field_name)
        pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if not re.match(pattern, value):
            raise ValidationError(f"Formato de '{field_name}' inválido", field_name)
        return value.strip().lower()

    @staticmethod
    def password(value):
        if not value:
            raise ValidationError("La contraseña es requerida", "password")
        if len(value) < 6:
            raise ValidationError(
                "La contraseña debe tener al menos 6 caracteres", "password"
            )
        if not re.search(r"[A-Z]", value):
            raise ValidationError(
                "La contraseña debe contener al menos una mayúscula", "password"
            )
        if not re.search(r"[0-9]", value):
            raise ValidationError(
                "La contraseña debe contener al menos un número", "password"
            )
        return value

    @staticmethod
    def role(value, allowed=("paciente", "profesional", "admin")):
        if value not in allowed:
            raise ValidationError(
                f"Rol inválido. Roles permitidos: {', '.join(allowed)}", "rol"
            )
        return value

    @staticmethod
    def positive_integer(value, field_name):
        try:
            num = int(value)
        except (TypeError, ValueError):
            raise ValidationError(f"'{field_name}' debe ser un número entero", field_name)
        if num <= 0:
            raise ValidationError(
                f"'{field_name}' debe ser un número positivo", field_name
            )
        return num


class MailService:
    @staticmethod
    def send_recovery_email(recipient_email, recovery_link):
        subject = "Recuperación de contraseña — PsyAI Connect"

        body_html = f"""
        <html>
        <body style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; padding: 20px; background-color: #f0f5fc;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; padding: 32px; border: 1.5px solid #D6E8FA;">
                <h2 style="color: #0D47A1; font-family: 'Lora', Georgia, serif;">Recuperación de contraseña</h2>
                <p style="color: #0D1F3C; font-size: 16px;">Has solicitado recuperar tu contraseña en PsyAI Connect.</p>
                <p style="color: #0D1F3C; font-size: 16px;">Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
                <div style="text-align: center; margin: 32px 0;">
                    <a href="{recovery_link}" style="background-color: #0D47A1; color: white; padding: 14px 28px; text-decoration: none; border-radius: 10px; font-weight: bold; display: inline-block;">Restablecer contraseña</a>
                </div>
                <p style="color: #7B92AC; font-size: 14px;">Este enlace expirará en 1 hora.</p>
                <p style="color: #7B92AC; font-size: 14px;">Si no solicitaste este cambio, puedes ignorar este correo en forma segura.</p>
            </div>
        </body>
        </html>
        """

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body="Recupera tu contraseña en PsyAI Connect: " + recovery_link,
                from_email=dj_settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            msg.attach_alternative(body_html, "text/html")
            msg.send(fail_silently=False)
            logger.info(f"Correo de recuperación enviado a {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"Error enviando correo de recuperación: {e}")
            return False

class AuthService:
    def __init__(self):
        self.repo = AuthRepository()
        self.security_repo = SecurityRepository()

    def _validate_register_data(self, data):
        nombre = data.get("nombre", "").strip() if data.get("nombre") else ""
        if not nombre:
            raise ValidationError("El campo 'nombre' es requerido", "nombre")

        email = data.get("email", "").strip() if data.get("email") else ""
        if not email:
            raise ValidationError("El campo 'email' es requerido", "email")
        pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if not re.match(pattern, email):
            raise ValidationError("Formato de 'email' inválido", "email")
        email = email.strip().lower()

        password = data.get("password", "")
        if isinstance(password, str):
            password = password.strip()
        if not password:
            raise ValidationError("La contraseña es requerida", "password")
        if len(password) < 6:
            raise ValidationError(
                "La contraseña debe tener al menos 6 caracteres", "password"
            )
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                "La contraseña debe contener al menos una mayúscula", "password"
            )
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                "La contraseña debe contener al menos un número", "password"
            )

        rol = data.get("rol", "paciente")
        allowed = ("paciente", "profesional", "admin")
        if rol not in allowed:
            raise ValidationError(
                f"Rol inválido. Roles permitidos: {', '.join(allowed)}", "rol"
            )

        edad = data.get("edad")
        if edad is not None:
            try:
                edad = int(edad)
                if edad < 1 or edad > 120:
                    raise ValidationError(
                        "La edad debe estar entre 1 y 120", "edad"
                    )
            except (TypeError, ValueError):
                raise ValidationError("'edad' debe ser un número entero", "edad")

        return {
            "nombre": nombre,
            "email": email,
            "password": password,
            "rol": rol,
            "edad": edad,
        }

    def _validate_login_data(self, data):
        email = data.get("email", "").strip().lower() if data.get("email") else ""
        if not email:
            raise ValidationError("El campo 'email' es requerido", "email")

        password = data.get("password", "")
        if isinstance(password, str):
            password = password.strip()
        if not password:
            raise ValidationError("El campo 'password' es requerido", "password")

        return {"email": email, "password": password}

    def _validate_forgot_password_data(self, data):
        email = data.get("email", "").strip() if data.get("email") else ""
        if not email:
            raise ValidationError("El campo 'email' es requerido", "email")
        pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if not re.match(pattern, email):
            raise ValidationError("Formato de 'email' inválido", "email")
        return {"email": email.strip().lower()}

    def _validate_reset_password_data(self, data):
        token = data.get("token", "").strip() if data.get("token") else ""
        if not token:
            raise ValidationError("El campo 'token' es requerido", "token")

        password = data.get("new_password", "")
        if not password:
            raise ValidationError("La contraseña es requerida", "password")
        if len(password) < 6:
            raise ValidationError(
                "La contraseña debe tener al menos 6 caracteres", "password"
            )
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                "La contraseña debe contener al menos una mayúscula", "password"
            )
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                "La contraseña debe contener al menos un número", "password"
            )

        return {"token": token, "password": password}

    def register_user(self, data):
        try:
            validated = self._validate_register_data(data)
        except ValidationError as e:
            return {"success": False, "message": e.message}, 400

        confirmar = data.get("confirm_password") or ""
        if validated["password"] != confirmar:
            return {"success": False, "message": "Las contraseñas no coinciden"}, 400
        if not data.get("genero"):
            return {"success": False, "message": "El género es requerido"}, 400

        nombre = validated["nombre"]
        email = validated["email"]
        password = validated["password"]
        rol = validated["rol"]
        genero = data.get("genero", "")
        edad = validated.get("edad")

        bloqueado, retry_after = self.security_repo.check_rate_limit(f"register:{email}")
        if bloqueado:
            return {
                "success": False,
                "message": f"Límite de intentos alcanzado. Intenta en {retry_after // 60} minutos.",
            }, 429

        if self.repo.user_exists_by_email(email):
            self.security_repo.register_rate_limit_hit(f"register:{email}")
            return {"success": False, "message": "El correo ya está registrado"}, 409

        self.repo.create_user(
            nombre, email, SecurityHelper.hash_password(password), rol, genero, edad
        )
        self.security_repo.reset_rate_limit(f"register:{email}")
        return {"success": True, "message": "Registro exitoso"}, 201

    def login_user(self, data, ip_address):
        try:
            validated = self._validate_login_data(data)
        except ValidationError as e:
            return {"success": False, "message": e.message}, 400, None

        email = validated["email"]
        password = validated["password"]
        rol = data.get("rol") or "paciente"

        bloqueado, retry_after = self.security_repo.check_brute_force(email)
        if bloqueado:
            return {
                "success": False,
                "message": f"Cuenta bloqueada. Intenta en {retry_after // 60} minutos.",
                "retry_after": retry_after,
            }, 429, None

        usuario = self.repo.get_user_by_email(email, admin_only=(rol == "admin"))
        if not usuario:
            return (
                {"success": False, "message": "Credenciales incorrectas o cuenta suspendida"},
                401,
                None,
            )
        if usuario["rol"] != rol:
            return (
                {"success": False, "message": f"Este usuario no tiene rol de {rol}"},
                403,
                None,
            )

        if not usuario.get("activo", True):
            return (
                {"success": False, "message": "Tu cuenta ha sido suspendida. Contacta al administrador."},
                403,
                None,
            )

        stored_hash = usuario.get("contrasena")
        if not SecurityHelper.verify_password(password, stored_hash):
            self.security_repo.register_failed_attempt(email)
            return (
                {"success": False, "message": "Credenciales incorrectas"},
                401,
                None,
            )

        if stored_hash and not SecurityHelper.is_sha256_hash(stored_hash):
            self.repo.update_password(
                usuario["idUsuario"], SecurityHelper.hash_password(password)
            )

        self.security_repo.reset_failed_attempts(email)
        self.repo.register_login_event(usuario["idUsuario"], email, ip_address)

        session_user = {
            "id": usuario["idUsuario"],
            "nombre": usuario["nombre"],
            "email": usuario["email"],
            "rol": usuario["rol"],
            "fotoPerfil": usuario.get("fotoPerfil"),
        }

        if usuario["rol"] == "paciente":
            redirect_url = "patient.dashboard.html"
        elif usuario["rol"] == "profesional":
            redirect_url = "professional.dashboard.html"
        else:
            redirect_url = "admin.dashboard.html"

        payload = {
            "success": True,
            "message": "Login exitoso",
            "usuario": session_user,
            "idUsuario": usuario["idUsuario"],
            "nombre": usuario["nombre"],
            "rol": usuario["rol"],
            "redirect": redirect_url,
            "fotoPerfil": usuario.get("fotoPerfil"),
        }
        return payload, 200, session_user

    def recover_password(self, email, request_host=None):
        try:
            validated = self._validate_forgot_password_data({"email": email})
        except ValidationError as e:
            return {"success": False, "message": e.message}, 400

        email = validated["email"]

        bloqueado, retry_after = self.security_repo.check_rate_limit(f"recovery:{email}")
        if bloqueado:
            return {
                "success": False,
                "message": f"Límite de intentos alcanzado. Intenta en {retry_after // 60} minutos.",
            }, 429

        self.security_repo.register_rate_limit_hit(f"recovery:{email}")

        existe = self.repo.active_user_exists_by_email(email)
        recovery_link = None
        email_sent = False

        if existe:
            token = secrets.token_urlsafe(32)
            expires = timezone.now() + timedelta(hours=1)
            self.repo.create_password_recovery_token(email, token, expires)
            host = request_host or "localhost"
            recovery_link = f"http://{host}/recover?token={token}"
            email_sent = MailService.send_recovery_email(email, recovery_link)

            if not email_sent:
                print(
                    "\n[RECUPERAR PASSWORD] No se pudo enviar correo por proveedor externo.",
                    flush=True,
                )
                print(f"[RECUPERAR PASSWORD] Email: {email}", flush=True)
                print(f"[RECUPERAR PASSWORD] Enlace local: {recovery_link}\n", flush=True)

        if not existe:
            return (
                {"success": False, "message": "No existe una cuenta con ese correo electrónico."},
                404,
            )

        payload = {"success": True, "message": "Fue enviado al correo."}
        env = os.getenv("DJANGO_SETTINGS_MODULE", "")
        if (
            recovery_link
            and not email_sent
            and "production" not in env.lower()
        ):
            payload["recovery_link"] = recovery_link

        return payload, 200

    def reset_password(self, data):
        try:
            validated = self._validate_reset_password_data(data)
        except ValidationError as e:
            return {"success": False, "message": e.message}, 400

        token = validated["token"]
        new_password = validated["password"]
        confirmar = data.get("confirm_password", "")

        if new_password != confirmar:
            return {"success": False, "message": "Las contraseñas no coinciden"}, 400

        user_id = self.repo.validate_recovery_token(token)
        if not user_id:
            return {"success": False, "message": "Token inválido o expirado"}, 400

        self.repo.invalidate_recovery_token(token)
        self.repo.update_password(user_id, SecurityHelper.hash_password(new_password))

        return {"success": True, "message": "Contraseña actualizada exitosamente"}, 200