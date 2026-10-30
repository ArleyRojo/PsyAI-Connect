import os

from django.contrib.auth import login as django_login
from django.middleware.csrf import get_token
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    VerifyEmailSerializer,
    TOTPSetupSerializer,
    TOTPVerifySerializer,
    TOTPDisableSerializer,
)
from apps.authentication.services import AuthService
from apps.authentication.models import Register


auth_service = AuthService()


class CsrfTokenView(APIView):
    """
    Endpoint para obtener el token CSRF.
    El frontend debe llamarlo antes de hacer peticiones POST/PUT/DELETE.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # Sin autenticación requerida

    def get(self, request):
        token = get_token(request)
        return Response({"csrfToken": token})


class VerifyEmailView(APIView):
    """
    Verifica el email del usuario usando el token enviado por correo.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        user_id = auth_service.repo.validate_email_verification_token(token)
        if not user_id:
            return Response(
                {"success": False, "message": "Token inválido o expirado"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        auth_service.repo.invalidate_email_verification_token(token)
        auth_service.repo.mark_email_verified(user_id)

        return Response(
            {"success": True, "message": "Correo verificado correctamente. Ya puedes iniciar sesión."},
            status=status.HTTP_200_OK,
        )


auth_service = AuthService()


class TOTPSetupView(APIView):
    """
    Inicia la configuración de 2FA (TOTP) para el usuario autenticado.
    Devuelve el secreto, URI y QR code en SVG.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        user_email = request.user.email

        # Crear/regenerar dispositivo TOTP
        device = auth_service.create_totp_device(user_id, name=request.GET.get("name", ""))
        if not device:
            return Response(
                {"success": False, "message": "No se pudo crear dispositivo 2FA"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        uri = auth_service.get_totp_provisioning_uri(user_id, request.user.email)
        qr_svg = auth_service.get_totp_qr_code_svg(user_id, request.user.email)

        return Response({
            "success": True,
            "secret": device.secret,
            "provisioning_uri": uri,
            "qr_code_svg": qr_svg,
            "message": "Escanea el código QR con tu app de autenticación (Google Authenticator, Authy, etc.)",
        }, status=status.HTTP_200_OK)


class TOTPConfirmView(APIView):
    """
    Confirma el dispositivo TOTP verificando el primer token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        user_id = request.user.id

        success, message = auth_service.confirm_totp_device(user_id, token)
        if not success:
            return Response(
                {"success": False, "message": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"success": True, "message": message}, status=status.HTTP_200_OK)


class TOTPDisableView(APIView):
    """
    Desactiva/elimina el 2FA del usuario (requiere contraseña actual).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TOTPDisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data["password"]
        user_id = request.user.id

        # Verificar contraseña actual
        try:
            user = Register.objects.get(idUsuario=user_id)
        except Register.DoesNotExist:
            return Response(
                {"success": False, "message": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        from apps.authentication.security import SecurityHelper
        if not SecurityHelper.verify_password(password, user.contrasena):
            return Response(
                {"success": False, "message": "Contraseña incorrecta"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        auth_service.disable_totp_device(user_id)
        return Response({"success": True, "message": "2FA desactivado correctamente"}, status=status.HTTP_200_OK)


class TOTPStatusView(APIView):
    """
    Consulta el estado del 2FA del usuario actual.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        device = auth_service.get_totp_device(user_id)

        return Response({
            "enabled": device is not None and device.confirmed,
            "device": device.to_dict() if device else None,
            "required_for_role": auth_service.require_totp_for_role(request.user.rol),
        }, status=status.HTTP_200_OK)


class TOTPVerifyLoginView(APIView):
    """
    Verifica el token TOTP durante el login (cuando el usuario ya tiene 2FA activado).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        # Obtener user_id de la sesión temporal de login 2FA
        user_id = request.session.get("pending_2fa_user_id")
        if not user_id:
            return Response(
                {"success": False, "message": "Sesión de 2FA expirada o inválida"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not auth_service.verify_totp_token(user_id, token):
            return Response(
                {"success": False, "message": "Código 2FA inválido"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Login exitoso - completar el login
        try:
            user_model = Register.objects.get(idUsuario=user_id)
        except Register.DoesNotExist:
            return Response(
                {"success": False, "message": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verificar estado de la cuenta antes de completar login
        if not user_model.activo or user_model.estadoCuenta != "Activa":
            return Response(
                {"success": False, "message": "Tu cuenta ha sido suspendida. Contacta al administrador."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Limpiar sesión temporal
        request.session.pop("pending_2fa_user_id", None)

        # Datos de sesión
        session_user = {
            "id": user_model.idUsuario,
            "nombre": user_model.nombre,
            "email": user_model.email,
            "rol": user_model.rol,
            "fotoPerfil": user_model.fotoPerfil,
        }
        request.session["usuario"] = session_user
        request.session["idUsuario"] = user_model.idUsuario
        request.session["nombre"] = user_model.nombre
        request.session["rol"] = user_model.rol
        request.session["fotoPerfil"] = user_model.fotoPerfil
        request.session.modified = True

        return Response({
            "success": True,
            "message": "Login con 2FA exitoso",
            "usuario": session_user,
            "redirect": "/patient.dashboard.html" if user_model.rol == "paciente" else (
                "/professional.dashboard.html" if user_model.rol == "profesional" else "/admin.dashboard.html"
            ),
        }, status=status.HTTP_200_OK)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = auth_service.register_user(serializer.validated_data, request)
        return Response(payload, status=status_code)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = request.META.get(
            "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown")
        )
        if "," in ip_address:
            ip_address = ip_address.split(",")[0].strip()

        payload, status_code, session_user = auth_service.login_user(
            serializer.validated_data, ip_address
        )

        if session_user:
            # Obtener el modelo de usuario real
            try:
                user_model = Register.objects.get(idUsuario=session_user["id"])
            except Register.DoesNotExist:
                return Response(
                    {"success": False, "message": "Usuario no encontrado"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Verificar si el usuario tiene 2FA activado y confirmado
            if auth_service.is_totp_enabled(user_model.idUsuario):
                # Guardar user_id en sesión temporal para verificación 2FA
                request.session["pending_2fa_user_id"] = user_model.idUsuario
                request.session.modified = True

                # Respuesta indicando que se requiere 2FA
                return Response({
                    "success": True,
                    "requires_2fa": True,
                    "message": "Se requiere autenticación de dos factores. Introduce el código de tu app de autenticación.",
                    "user_id": user_model.idUsuario,
                }, status=status.HTTP_200_OK)

            # Sin 2FA - login directo

            request.session["usuario"] = session_user
            request.session["idUsuario"] = session_user["id"]
            request.session["nombre"] = session_user["nombre"]
            request.session["rol"] = session_user["rol"]
            request.session["fotoPerfil"] = session_user.get("fotoPerfil")
            request.session.modified = True

        return Response(payload, status=status_code)


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        request.session.flush()
        return Response(
            {"success": True, "message": "Sesion cerrada"},
            status=status.HTTP_200_OK,
        )


class SessionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        id_usuario = request.session.get("idUsuario")
        if id_usuario:
            fp = request.session.get("fotoPerfil")
            if fp and not fp.startswith("http"):
                from django.conf import settings

                fpath = os.path.join(settings.MEDIA_ROOT, "uploads", fp)
                if not os.path.exists(fpath):
                    request.session.pop("fotoPerfil", None)
                    fp = None
            return Response(
                {
                    "success": True,
                    "logged_in": True,
                    "usuario": {
                        "idUsuario": request.session.get("idUsuario"),
                        "id": request.session.get("idUsuario"),
                        "nombre": request.session.get("nombre"),
                        "rol": request.session.get("rol"),
                    },
                    "idUsuario": request.session.get("idUsuario"),
                    "nombre": request.session.get("nombre"),
                    "rol": request.session.get("rol"),
                    "fotoPerfil": fp,
                }
            )
        return Response({"success": True, "logged_in": False})


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        payload, status_code = auth_service.recover_password(email, request)
        return Response(payload, status=status_code)


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = auth_service.reset_password(serializer.validated_data)
        return Response(payload, status=status_code)


def social_login_redirect(request):
    rol = request.session.get("rol", "paciente")
    if rol == "admin":
        return HttpResponseRedirect("/admin.dashboard.html")
    elif rol == "profesional":
        return HttpResponseRedirect("/professional.dashboard.html")
    else:
        return HttpResponseRedirect("/patient.dashboard.html")
