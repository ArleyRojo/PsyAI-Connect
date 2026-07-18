import logging
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.authentication.models import (
    IntentosFallidos,
    Login,
    RecoveryTokens,
    Register,
)

logger = logging.getLogger(__name__)


class AuthRepository:
    def user_exists_by_email(self, email):
        return Register.objects.filter(email=email).exists()

    def create_user(self, nombre, email, password_hash, rol, genero=None, edad=None):
        user = Register(
            email=Register.objects.normalize_email(email),
            nombre=nombre,
            contrasena=password_hash,
            rol=rol,
        )
        user.set_unusable_password()
        user.save()
        return user.idUsuario

    def get_user_by_email(self, email, *, admin_only=False):
        qs = Register.objects.filter(email=email, estadoCuenta="Activa")
        if admin_only:
            qs = qs.filter(rol="admin")
        user = qs.first()
        if user:
            return user.to_dict()
        return None

    def active_user_exists_by_email(self, email):
        return Register.objects.filter(
            email=email, estadoCuenta="Activa"
        ).exists()

    def create_password_recovery_token(self, email, token, expires):
        user = Register.objects.filter(email=email).first()
        if user:
            RecoveryTokens.objects.filter(
                idUsuario=user, used=False
            ).update(used=True)
            RecoveryTokens.objects.create(
                idUsuario=user, token=token, expires=expires
            )

    def validate_recovery_token(self, token):
        rt = RecoveryTokens.objects.filter(token=token, used=False).first()
        if not rt:
            return None
        now = timezone.now()
        if rt.expires < now:
            return None
        return rt.idUsuario_id

    def invalidate_recovery_token(self, token):
        rt = RecoveryTokens.objects.filter(token=token).first()
        if rt:
            rt.used = True
            rt.save(update_fields=["used"])
            return True
        return False

    def update_password(self, user_id, new_password_hash):
        updated = Register.objects.filter(idUsuario=user_id).update(
            contrasena=new_password_hash
        )
        return updated > 0

    def register_login_event(self, user_id, email, ip_address="unknown"):
        try:
            Login.objects.create(
                idUsuario_id=user_id,
                email=email,
                ultimoAcceso=timezone.now(),
            )
        except Exception as e:
            logger.error(f"Error registering login event: {e}")


class SecurityRepository:
    def check_brute_force(self, email):
        try:
            row = IntentosFallidos.objects.filter(email=email).first()
            if not row:
                return False, 0
            if row.intentos < 5:
                return False, 0
            if not row.bloqueado_hasta:
                return False, 0
            now = timezone.now()
            if row.bloqueado_hasta <= now:
                return False, 0
            segundos = int((row.bloqueado_hasta - now).total_seconds())
            return True, segundos
        except Exception:
            return False, 0

    def register_failed_attempt(self, email):
        now = timezone.now()
        try:
            row = IntentosFallidos.objects.filter(email=email).first()
            if row:
                row.intentos += 1
                row.ultimo_intento = now
                if row.intentos >= 5:
                    row.bloqueado_hasta = now + timedelta(minutes=15)
                row.save(update_fields=["intentos", "ultimo_intento", "bloqueado_hasta"])
            else:
                IntentosFallidos.objects.create(
                    email=email, intentos=1, ultimo_intento=now
                )
        except Exception:
            return

    def reset_failed_attempts(self, email):
        try:
            row = IntentosFallidos.objects.filter(email=email).first()
            if row:
                row.intentos = 0
                row.bloqueado_hasta = None
                row.save(update_fields=["intentos", "bloqueado_hasta"])
        except Exception:
            return