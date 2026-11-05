import uuid

from django.shortcuts import redirect
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from apps.authentication.models import Register


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def clean_email(self, email):
        return email

    def pre_social_login(self, request, sociallogin):
        """
        Si el email del login social (Google) no existe en la BD,
        redirige al registro antes de permitir asociar la cuenta social.
        """
        email = sociallogin.account.extra_data.get("email")
        if email:
            try:
                Register.objects.get(email__iexact=email)
                # El usuario existe, permitir login normal
                return None
            except Register.DoesNotExist:
                # Usuario no registrado: redirigir a registro con indicador de Google
                request.session["social_pending_email"] = email
                return redirect("/register.html?google=1")
        return None

    def new_user(self, request, sociallogin):
        user = Register()
        user.rol = "paciente"
        user.contrasena = uuid.uuid4().hex
        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Crea/actualiza el usuario desde un inicio de sesión social (Google).
        Trabaja sobre sociallogin.user (no crea Register nuevo) para que
        allauth pueda hacer el login y crear el SocialAccount.
        """
        extra = sociallogin.account.extra_data

        user = sociallogin.user

        user.rol = "paciente"
        user.email = extra.get("email") or user.email or ""
        user.nombre = (
            extra.get("name") or extra.get("given_name") or extra.get("first_name") or user.email
        )
        # Contraseña aleatoria hasheada (argon2) para satisfecer NOT NULL en PostgreSQL.
        user.set_password(uuid.uuid4().hex)
        user.email_verificado = True  # Google ya verificó el correo

        if extra.get("picture"):
            user.fotoPerfil = extra["picture"]

        # Guarda el usuario Y crea el SocialAccount (allauth lo requiere)
        sociallogin.save(request)

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
            request.session["usuario"] = user.to_session_dict()
            request.session["idUsuario"] = user.idUsuario
            request.session["nombre"] = user.nombre
            request.session["rol"] = user.rol
            request.session["fotoPerfil"] = user.fotoPerfil
            request.session.modified = True
