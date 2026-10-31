import logging
import os
import re
import secrets
from datetime import datetime, timedelta

from django.conf import settings as dj_settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

try:
    import pyotp
    import qrcode
    import qrcode.image.svg
    TOTP_AVAILABLE = True
except ImportError:
    pyotp = None
    qrcode = None
    TOTP_AVAILABLE = False

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

        from urllib.parse import urlparse
        parsed = urlparse(recovery_link)
        site_url = f"{parsed.scheme}://{parsed.netloc}"

        body_html = render_to_string("emails/password_recovery.html", {
            "recovery_link": recovery_link,
            "site_url": site_url,
        })

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

        rol = (data.get("rol", "paciente") or "paciente").strip().lower()
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

    def register_user(self, data, request=None):
        try:
            validated = self._validate_register_data(data)
        except ValidationError as e:
            return {"success": False, "message": e.message}, 400

        confirmar = data.get("confirm_password") or ""
        if validated["password"] != confirmar:
            return {"success": False, "message": "Las contraseñas no coinciden"}, 400
        if not data.get("genero"):
            return {"success": False, "message": "El género es requerido"}, 400

        # Validar aceptación de términos y política de privacidad
        if not data.get("acepta_terminos"):
            return {"success": False, "message": "Debes aceptar los términos y la política de privacidad"}, 400

        nombre = validated["nombre"]
        email = validated["email"]
        password = validated["password"]
        rol = validated["rol"]
        genero = data.get("genero", "")
        edad = validated.get("edad")

        # Validar edad mínima
        from django.conf import settings
        edad_minima = getattr(settings, "EDAD_MINIMA_REGISTRO", 18)
        if edad is not None and edad < edad_minima:
            return {"success": False, "message": f"Debes tener al menos {edad_minima} años para registrarte"}, 400

        bloqueado, retry_after = self.security_repo.check_rate_limit(f"register:{email}")
        if bloqueado:
            return {
                "success": False,
                "message": f"Límite de intentos alcanzado. Intenta en {retry_after // 60} minutos.",
            }, 429

        if self.repo.user_exists_by_email(email):
            self.security_repo.register_rate_limit_hit(f"register:{email}")
            return {"success": False, "message": "El correo ya está registrado"}, 409

        # Para profesionales, requerir verificación de email obligatoria
        email_verificado = (rol != "profesional")
        # Por seguridad, también podríamos requerir verificación para todos en producción
        # if not settings.DEBUG:
        #     email_verificado = False

        user_id = self.repo.create_user(
            nombre, email, SecurityHelper.hash_password(password), rol, genero, edad,
            email_verificado=email_verificado
        )

        # Guardar consentimiento de términos y privacidad
        from apps.authentication.models import ConsentimientoUsuario
        from django.conf import settings
        legal_version = getattr(settings, "LEGAL_VERSION", "2026-10-26")
        client_ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")) if request else ""
        user_agent = request.META.get("HTTP_USER_AGENT", "") if request else ""

        ConsentimientoUsuario.objects.create(
            idUsuario_id=user_id,
            tipo="terminos_privacidad",
            version=getattr(settings, "LEGAL_VERSION", "2026-10-26"),
            aceptado=True,
            ip=client_ip.split(",")[0].strip() if client_ip else None,
            userAgent=user_agent,
        )

        # Si es profesional o email no verificado, crear token de verificación y enviar email
        if not email_verificado:
            self._create_and_send_verification_email(user_id, email, request)

        self.security_repo.reset_rate_limit(f"register:{email}")
        if email_verificado:
            return {"success": True, "message": "Registro exitoso"}, 201
        else:
            return {
                "success": True,
                "message": "Registro exitoso. Revisa tu correo para verificar tu cuenta.",
                "email_verification_required": True
            }, 201

    def _create_and_send_verification_email(self, user_id, email, request=None):
        """Crea token de verificación y envía email de verificación."""
        token = secrets.token_urlsafe(32)
        expires = timezone.now() + timedelta(hours=24)  # 24 horas para verificar
        self.repo.create_email_verification_token(user_id, token, expires)

        host = request.get_host() if request else "localhost"
        scheme = request.scheme if request else "http"
        from django.conf import settings
        if not settings.DEBUG:
            scheme = "https"
        verification_link = f"{scheme}://{host}/verify-email.html?token={token}"

        subject = "Verifica tu correo — PsyAI Connect"
        body_html = f"""
        <p>Hola,</p>
        <p>Gracias por registrarte en PsyAI Connect. Para completar tu registro, verifica tu correo electrónico:</p>
        <p><a href="{verification_link}" style="background:#1565C0;color:#fff;padding:12px 24px;text-decoration:none;border-radius:4px;display:inline-block;">Verificar mi correo</a></p>
        <p>O copia este enlace en tu navegador: {verification_link}</p>
        <p>Este enlace expira en 24 horas.</p>
        <hr>
        <small>Si no te registraste en PsyAI Connect, ignora este correo.</small>
        """

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=f"Verifica tu correo en PsyAI Connect: {verification_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(body_html, "text/html")
            msg.send(fail_silently=False)
            logger.info(f"Correo de verificación enviado a {email}")
        except Exception as e:
            logger.error(f"Error enviando correo de verificación: {e}")

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
            logger.warning(
                "Login 403 – rol mismatch: email=%s, esperado=%s, real=%s",
                email, rol, usuario["rol"],
            )
            return (
                {"success": False, "message": f"Este usuario no tiene rol de {rol}"},
                403,
                None,
            )

        if not usuario.get("activo", True):
            logger.warning(
                "Login 403 – cuenta inactiva: email=%s, id=%s",
                email, usuario.get("idUsuario"),
            )
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

        if SecurityHelper.needs_upgrade(stored_hash):
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

    def recover_password(self, email, request=None):
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
            host = request.get_host() if request else "localhost"
            scheme = request.scheme if request else "http"
            # Forzar HTTPS en producción (DEBUG=False)
            from django.conf import settings
            if not settings.DEBUG:
                scheme = "https"
            recovery_link = f"{scheme}://{host}/reset-password.html?token={token}"
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

    # ── TOTP / 2FA ────────────────────────────────────────────────

    def _check_totp_available(self):
        if not TOTP_AVAILABLE:
            raise ValidationError("Funcionalidad 2FA no disponible. Instale pyotp y qrcode.")

    def get_totp_device(self, user_id):
        """Obtiene o crea el dispositivo TOTP del usuario."""
        from apps.authentication.models import TOTPDevice
        try:
            return TOTPDevice.objects.get(idUsuario_id=user_id)
        except TOTPDevice.DoesNotExist:
            return None

    def create_totp_device(self, user_id, name=""):
        """Crea un nuevo secreto TOTP para el usuario (aún no confirmado)."""
        self._check_totp_available()

        device = self.get_totp_device(user_id)
        if device:
            # Regenerar secreto si ya existe
            device.secret = pyotp.random_base32()
            device.name = name
            device.confirmed = False
            device.save()
        else:
            device = TOTPDevice.objects.create(
                idUsuario_id=user_id,
                secret=pyotp.random_base32(),
                name=name,
                confirmed=False,
            )
        return device

    def get_totp_provisioning_uri(self, user_id, email):
        """Genera la URI para QR code (otpauth://...)."""
        self._check_totp_available()
        device = self.get_totp_device(user_id)
        if not device:
            return None
        totp = pyotp.TOTP(device.secret)
        return totp.provisioning_uri(name=email, issuer_name="PsyAI Connect")

    def get_totp_qr_code_svg(self, user_id, email):
        """Genera el código QR en formato SVG."""
        self._check_totp_available()
        uri = self.get_totp_provisioning_uri(user_id, email)
        if not uri:
            return None
        qr = qrcode.make(uri, image_factory=qrcode.image.svg.SvgImage)
        from io import BytesIO
        buffer = BytesIO()
        qr.save(buffer)
        return buffer.getvalue().decode("utf-8")

    def verify_totp_token(self, user_id, token):
        """Verifica un token TOTP (código de 6 dígitos)."""
        self._check_totp_available()
        device = self.get_totp_device(user_id)
        if not device or not device.confirmed:
            return False
        totp = pyotp.TOTP(device.secret)
        return totp.verify(token, valid_window=1)  # ventana de 30s antes/después

    def confirm_totp_device(self, user_id, token):
        """Confirma el dispositivo TOTP tras verificar el primer token."""
        self._check_totp_available()
        device = self.get_totp_device(user_id)
        if not device:
            return False, "Dispositivo no encontrado"
        if device.confirmed:
            return False, "El dispositivo ya está confirmado"
        if not self.verify_totp_token(user_id, token):
            return False, "Código inválido"
        device.confirmed = True
        device.last_used = timezone.now()
        device.save()
        return True, "2FA activado correctamente"

    def disable_totp_device(self, user_id):
        """Desactiva/elimina el dispositivo 2FA del usuario."""
        device = self.get_totp_device(user_id)
        if device:
            device.delete()
            return True
        return False

    def is_totp_enabled(self, user_id):
        """Verifica si el usuario tiene 2FA activado y confirmado."""
        device = self.get_totp_device(user_id)
        return device is not None and device.confirmed

    def require_totp_for_role(self, role):
        """Determina si el rol requiere 2FA obligatorio."""
        return role in ("admin", "profesional")