import logging
import os

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
)
from apps.authentication.services import AuthService

logger = logging.getLogger(__name__)


auth_service = AuthService()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload, status_code = auth_service.register_user(serializer.validated_data)
        return Response(payload, status=status_code)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        logger.info("LoginView.post called: method=%s, path=%s", request.method, request.path)
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
        request_host = request.get_host()
        payload, status_code = auth_service.recover_password(email, request_host)
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
