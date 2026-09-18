from apps.authentication.models import Register


class EmailBackend:
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email", username)
        if not email:
            return None
        try:
            user = Register.objects.get(email=email)
        except Register.DoesNotExist:
            return None

        from apps.authentication.security import SecurityHelper

        if SecurityHelper.verify_password(password, user.contrasena):
            return user
        return None

    def get_user(self, user_id):
        try:
            return Register.objects.get(pk=user_id)
        except Register.DoesNotExist:
            return None
