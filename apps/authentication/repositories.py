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

    def create_user(self, nombre, email, password_hash, rol, genero=None, edad=None, email_verificado=True):
        user = Register(
            email=Register.objects.normalize_email(email),
            nombre=nombre,
            contrasena=password_hash,
            rol=(rol or "").strip().lower(),
            email_verificado=email_verificado,
        )
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

    def create_email_verification_token(self, user_id, token, expires):
        user = Register.objects.filter(idUsuario=user_id).first()
        if user:
            EmailVerificationToken.objects.filter(
                idUsuario=user, used=False
            ).update(used=True)
            EmailVerificationToken.objects.create(
                idUsuario=user, token=token, expires=expires
            )

    def validate_email_verification_token(self, token):
        vt = EmailVerificationToken.objects.filter(token=token, used=False).first()
        if not vt:
            return None
        now = timezone.now()
        if vt.expires < now:
            return None
        return vt.idUsuario_id

    def invalidate_email_verification_token(self, token):
        vt = EmailVerificationToken.objects.filter(token=token).first()
        if vt:
            vt.used = True
            vt.save(update_fields=["used"])
            return True
        return False

    def mark_email_verified(self, user_id):
        updated = Register.objects.filter(idUsuario=user_id).update(email_verificado=True)
        return updated > 0

    def update_password(self, user_id, new_password_hash):
        updated = Register.objects.filter(idUsuario=user_id).update(
            password=new_password_hash
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

    def check_rate_limit(self, key, max_attempts=10, window_minutes=60, lockout_minutes=30):
        try:
            row = IntentosFallidos.objects.filter(email=key).first()
            if not row:
                return False, 0
            if row.bloqueado_hasta:
                now = timezone.now()
                if row.bloqueado_hasta > now:
                    segundos = int((row.bloqueado_hasta - now).total_seconds())
                    return True, segundos
            if row.intentos >= max_attempts:
                now = timezone.now()
                if row.ultimo_intento:
                    elapsed = (now - row.ultimo_intento).total_seconds() / 60
                    if elapsed < window_minutes:
                        row.bloqueado_hasta = now + timedelta(minutes=lockout_minutes)
                        row.save(update_fields=["bloqueado_hasta"])
                        return True, lockout_minutes * 60
                    else:
                        row.intentos = 0
                        row.bloqueado_hasta = None
                        row.save(update_fields=["intentos", "bloqueado_hasta"])
            return False, 0
        except Exception:
            return False, 0

    def register_rate_limit_hit(self, key):
        now = timezone.now()
        try:
            row = IntentosFallidos.objects.filter(email=key).first()
            if row:
                row.intentos += 1
                row.ultimo_intento = now
                row.save(update_fields=["intentos", "ultimo_intento"])
            else:
                IntentosFallidos.objects.create(
                    email=key, intentos=1, ultimo_intento=now
                )
        except Exception:
            return

    def reset_rate_limit(self, key):
        try:
            row = IntentosFallidos.objects.filter(email=key).first()
            if row:
                row.intentos = 0
                row.bloqueado_hasta = None
                row.save(update_fields=["intentos", "bloqueado_hasta"])
        except Exception:
            return

    # ── TOTP / 2FA ────────────────────────────────────────────────

    def get_totp_device(self, user_id):
        from apps.authentication.models import TOTPDevice
        try:
            return TOTPDevice.objects.get(idUsuario_id=user_id)
        except TOTPDevice.DoesNotExist:
            return None

    def create_totp_device(self, user_id, name="", secret=None):
        from apps.authentication.models import TOTPDevice
        device, created = TOTPDevice.objects.update_or_create(
            idUsuario_id=user_id,
            defaults={
                "name": name,
                "secret": secret,
                "confirmed": False,
            }
        )
        return device

    def delete_totp_device(self, user_id):
        from apps.authentication.models import TOTPDevice
        TOTPDevice.objects.filter(idUsuario_id=user_id).delete()

    def get_totp_device_by_user(self, user_id):
        from apps.authentication.models import TOTPDevice
        try:
            return TOTPDevice.objects.get(idUsuario_id=user_id)
        except TOTPDevice.DoesNotExist:
            return None