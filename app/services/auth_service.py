import secrets
import os
from datetime import datetime, timedelta

from flask import request as flask_request

from app.repositories.auth_repository import AuthRepository
from app.repositories.security_repository import SecurityRepository
from app.repositories.admin_repository import AdminRepository
from app.utils.security import SecurityHelper

admin_mod = AdminRepository()
from app.utils.mail import MailService
from app.schemas.auth_schemas import RegisterSchema, LoginSchema, ForgotPasswordSchema, ResetPasswordSchema
from app.schemas.base import SchemaValidationError


class AuthService:
    def __init__(self):
        self.repo = AuthRepository()
        self.security_repo = SecurityRepository()

    def register_user(self, data):
        try:
            validated = RegisterSchema.load(data)
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400

        confirmar = data.get("confirm_password") or ""
        if validated["password"] != confirmar:
            return {"success": False, "message": "Las contraseñas no coinciden"}, 400
        if not data.get("genero"):
            return {"success": False, "message": "El género es requerido"}, 400

        edad = validated.get("edad")
        if edad is not None and (edad < 1 or edad > 120):
            return {"success": False, "message": "La edad debe estar entre 1 y 120"}, 400

        nombre = validated["nombre"]
        email = validated["email"]
        password = validated["password"]
        rol = validated["rol"]
        genero = data.get("genero", "")

        if self.repo.user_exists_by_email(email):
            return {"success": False, "message": "El correo ya está registrado"}, 409

        self.repo.create_user(nombre, email, SecurityHelper.hash_password(password), rol, genero, edad)
        return {"success": True, "message": "Registro exitoso"}, 201

    def login_user(self, data, ip_address):
        try:
            validated = LoginSchema.load(data)
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400, None

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
            return {"success": False, "message": "Credenciales incorrectas o cuenta suspendida"}, 401, None
        if usuario["rol"] != rol:
            return {"success": False, "message": f"Este usuario no tiene rol de {rol}"}, 403, None

        stored_hash = usuario.get("contrasena")
        if not SecurityHelper.verify_password(password, stored_hash):
            self.security_repo.register_failed_attempt(email)
            admin_mod.registrar_evento_seguridad("Login fallido", f"Email: {email} - IP: {ip_address}")
            return {"success": False, "message": "Credenciales incorrectas"}, 401, None

        if stored_hash and not SecurityHelper.is_sha256_hash(stored_hash):
            self.repo.update_password(usuario["idUsuario"], SecurityHelper.hash_password(password))

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

    def recover_password(self, email):
        try:
            validated = ForgotPasswordSchema.load({"email": email})
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400
        email = validated["email"]

        existe = self.repo.active_user_exists_by_email(email)
        recovery_link = None
        email_sent = False

        if existe:
            token = secrets.token_urlsafe(32)
            expires = datetime.now() + timedelta(hours=1)
            self.repo.create_password_recovery_token(email, token, expires)
            recovery_link = f"{flask_request.host_url.rstrip('/')}/recover?token={token}"
            email_sent = MailService.send_recovery_email(email, recovery_link)

            if not email_sent:
                print("\n[RECUPERAR PASSWORD] No se pudo enviar correo por proveedor externo.", flush=True)
                print(f"[RECUPERAR PASSWORD] Email: {email}", flush=True)
                print(f"[RECUPERAR PASSWORD] Enlace local: {recovery_link}\n", flush=True)

        if not existe:
            return {"success": False, "message": "No existe una cuenta con ese correo electrónico."}, 404

        payload = {"success": True, "message": "Fue enviado al correo."}
        if recovery_link and not email_sent and os.getenv("FLASK_ENV", "development").lower() != "production":
            payload["recovery_link"] = recovery_link

        return payload, 200

    def reset_password(self, data):
        try:
            validated = ResetPasswordSchema.load(data)
        except SchemaValidationError as e:
            first_error = next(iter(e.errors.values()))
            return {"success": False, "message": first_error}, 400

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
