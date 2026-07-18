import os

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.services import AuthService


auth_service = AuthService()


class RegisterView(APIView):
    def post(self, request):
        payload, status_code = auth_service.register_user(request.data or {})
        return Response(payload, status=status_code)


class LoginView(APIView):
    def post(self, request):
        ip_address = request.META.get(
            "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown")
        )
        if "," in ip_address:
            ip_address = ip_address.split(",")[0].strip()

        payload, status_code, session_user = auth_service.login_user(
            request.data or {}, ip_address
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
    def post(self, request):
        request.session.flush()
        return Response(
            {"success": True, "message": "Sesion cerrada"},
            status=status.HTTP_200_OK,
        )


class SessionView(APIView):
    def get(self, request):
        id_usuario = request.session.get("idUsuario")
        if id_usuario:
            fp = request.session.get("fotoPerfil")
            if fp:
                from django.conf import settings

                fpath = os.path.join(settings.BASE_DIR, "static", "uploads", fp)
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
    def post(self, request):
        data = request.data or {}
        email = data.get("email", "").strip()
        request_host = request.get_host()
        payload, status_code = auth_service.recover_password(email, request_host)
        return Response(payload, status=status_code)


class ResetPasswordView(APIView):
    def post(self, request):
        data = request.data or {}
        payload, status_code = auth_service.reset_password(data)
        return Response(payload, status=status_code)
