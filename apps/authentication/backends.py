from apps.authentication.repositories import AuthRepository


class EmailBackend:
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email", username)
        if not email:
            return None
        user = AuthRepository().get_user_by_email_for_auth_or_none(email)
        if user is None:
            return None

        from apps.authentication.security import SecurityHelper

        if SecurityHelper.verify_password(password, user.contrasena):
            return user
        return None

    def get_user(self, user_id):
        return AuthRepository().get_user_by_pk_or_none(user_id)
