from django.dispatch import receiver
from allauth.account.signals import user_logged_in
from apps.authentication.models import Register


@receiver(user_logged_in)
def setup_session_on_login(request, user, **kwargs):
    if isinstance(user, Register):
        if not user.activo or user.estadoCuenta != "Activa":
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Tu cuenta ha sido suspendida. Contacta al administrador.")
        foto = user.fotoPerfil

        if not foto:
            from allauth.socialaccount.models import SocialAccount

            try:
                sa = SocialAccount.objects.get(user=user, provider="google")
                picture = sa.extra_data.get("picture")
                if picture:
                    foto = picture
                    user.fotoPerfil = foto
                    user.save(update_fields=["fotoPerfil"])
            except SocialAccount.DoesNotExist:
                pass

        request.session["usuario"] = user.to_dict()
        request.session["idUsuario"] = user.idUsuario
        request.session["nombre"] = user.nombre
        request.session["rol"] = user.rol
        request.session["fotoPerfil"] = foto
        request.session.modified = True
