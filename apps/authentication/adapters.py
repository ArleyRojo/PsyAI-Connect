import uuid

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from apps.authentication.models import Register


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def clean_email(self, email):
        return email

    def new_user(self, request, sociallogin):
        user = Register()
        user.rol = "paciente"
        user.contrasena = uuid.uuid4().hex
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        extra = sociallogin.account.extra_data

        user.nombre = extra.get("name") or extra.get("first_name", "") or user.email
        user.email = extra.get("email", user.email)
        user.rol = "paciente"
        user.contrasena = uuid.uuid4().hex

        if extra.get("picture"):
            user.fotoPerfil = extra["picture"]

        user.save()
        self._create_perfil_paciente(user)
        self._setup_session(request, user)
        return user

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        extra = sociallogin.account.extra_data

        user.nombre = extra.get("name") or extra.get("first_name", "") or ""
        user.rol = "paciente"

        if extra.get("picture"):
            user.fotoPerfil = extra["picture"]

        return user

    def _create_perfil_paciente(self, user):
        from apps.patients.models import PerfilPaciente

        PerfilPaciente.objects.get_or_create(
            idPaciente=user,
            defaults={
                "consentimientoDatos": True,
                "consentimiento_chatbot": True,
            },
        )

    def _setup_session(self, request, user):
        if isinstance(user, Register):
            if not user.activo or user.estadoCuenta != "Activa":
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Tu cuenta ha sido suspendida. Contacta al administrador.")
            request.session["usuario"] = user.to_dict()
            request.session["idUsuario"] = user.idUsuario
            request.session["nombre"] = user.nombre
            request.session["rol"] = user.rol
            request.session["fotoPerfil"] = user.fotoPerfil
            request.session.modified = True
