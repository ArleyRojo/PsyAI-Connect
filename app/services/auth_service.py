# ============================================================
# ARCHIVO: services/auth_service.py
# ============================================================

import secrets
import os
from datetime import datetime, timedelta

from flask import request as flask_request

from app.repositories import auth_repository
from app.repositories.admin_repository import registrar_evento_seguridad
from app.utils.security import hash_password, verify_password
from app.utils.mail import send_recovery_email
from app.utils.validators import Validator, ValidationError


def register_user(data):
    try:
        # Valida y extrae cada campo del formulario de registro
        nombre = Validator.required((data.get("nombre") or "").strip(), "nombre")
        email = Validator.email((data.get("email") or "").strip())
        password = Validator.password(data.get("password") or "")
        confirmar = data.get("confirm_password") or ""
        rol = data.get("rol") or "paciente"
        genero = data.get("genero") or ""
        edad = data.get("edad")

        if password != confirmar:
            return {"success": False, "message": "Las contraseñas no coinciden"}, 400
        if rol not in ("paciente", "profesional"):
            return {"success": False, "message": "Rol inválido"}, 400
        if not genero:
            return {"success": False, "message": "El género es requerido"}, 400
        try:
            edad = Validator.integer(edad, "edad")
            if edad < 1 or edad > 120:
                raise ValidationError("La edad debe estar entre 1 y 120", "edad")
        except ValidationError as e:
            return {"success": False, "message": e.message}, 400
        # Verifica que el email no esté ya registrado
        if auth_repository.user_exists_by_email(email):
            return {"success": False, "message": "El correo ya está registrado"}, 409

        auth_repository.create_user(nombre, email, hash_password(password), rol, genero, edad)
        return {"success": True, "message": "Registro exitoso"}, 201

    except ValidationError as e:
        return {"success": False, "message": e.message}, 400


def login_user(data, ip_address):
    from app.repositories.security_repository import check_brute_force, register_failed_attempt, reset_failed_attempts

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    rol = data.get("rol") or "paciente"

    if not email or not password:
        return {"success": False, "message": "Email y contrasena requeridos"}, 400, None

    # Verifica si la cuenta está bloqueada por demasiados intentos fallidos
    bloqueado, retry_after = check_brute_force(email)
    if bloqueado:
        return {
            "success": False,
            "message": f"Cuenta bloqueada. Intenta en {retry_after // 60} minutos.",
            "retry_after": retry_after,
        }, 429, None

    usuario = auth_repository.get_user_by_email(email, admin_only=rol == "admin")
    if not usuario:
        return {"success": False, "message": "Credenciales incorrectas o cuenta suspendida"}, 401, None
    # Verifica que el rol coincida con el solicitado en el login
    if usuario["rol"] != rol:
        return {"success": False, "message": f"Este usuario no tiene rol de {rol}"}, 403, None

    stored_hash = usuario.get("contrasena")
    if not verify_password(password, stored_hash):
        register_failed_attempt(email)
        registrar_evento_seguridad("Login fallido", f"Email: {email} - IP: {ip_address}")
        return {"success": False, "message": "Credenciales incorrectas"}, 401, None

    # Login exitoso: reinicia contador de intentos y registra el evento
    reset_failed_attempts(email)
    auth_repository.register_login_event(usuario["idUsuario"], email, ip_address)

    session_user = {
        "id": usuario["idUsuario"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "rol": usuario["rol"],
        "fotoPerfil": usuario.get("fotoPerfil"),
    }

    # Redirige al dashboard correspondiente según el rol
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


def recover_password(email):
    if not email:
        return {"success": False, "message": "Email requerido"}, 400

    existe = auth_repository.active_user_exists_by_email(email)

    recovery_link = None
    email_sent = False

    if existe:
        # Genera un token seguro de 32 bytes y lo guarda con expiración de 1 hora
        token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(hours=1)
        auth_repository.create_password_recovery_token(email, token, expires)

        recovery_link = f"{flask_request.host_url.rstrip('/')}/recover?token={token}"
        email_sent = send_recovery_email(email, recovery_link)

        if not email_sent:
            print("\n[RECUPERAR PASSWORD] No se pudo enviar correo por proveedor externo.", flush=True)
            print(f"[RECUPERAR PASSWORD] Email: {email}", flush=True)
            print(f"[RECUPERAR PASSWORD] Enlace local: {recovery_link}\n", flush=True)

    if not existe:
        return {"success": False, "message": "No existe una cuenta con ese correo electr\u00f3nico."}, 404

    payload = {"success": True, "message": "Fue enviado al correo."}
    # En desarrollo, devuelve el enlace directamente si no se pudo enviar el email
    if recovery_link and not email_sent and os.getenv("FLASK_ENV", "development").lower() != "production":
        payload["recovery_link"] = recovery_link

    return payload, 200


def reset_password(data):
    token = data.get("token", "").strip()
    new_password = data.get("new_password", "")
    confirmar = data.get("confirm_password", "")

    if not token or not new_password:
        return {"success": False, "message": "Token y nueva contrase\u00f1a requeridos"}, 400
    if new_password != confirmar:
        return {"success": False, "message": "Las contrase\u00f1as no coinciden"}, 400

    try:
        new_password = Validator.password(new_password)
    except ValidationError as e:
        return {"success": False, "message": e.message}, 400

    # Valida que el token sea válido y no haya expirado
    user_id = auth_repository.validate_recovery_token(token)
    if not user_id:
        return {"success": False, "message": "Token inv\u00e1lido o expirado"}, 400

    auth_repository.invalidate_recovery_token(token)
    auth_repository.update_password(user_id, hash_password(new_password))

    return {"success": True, "message": "Contrase\u00f1a actualizada exitosamente"}, 200
