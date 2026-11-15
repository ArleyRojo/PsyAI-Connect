import logging
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.authentication.models import (
    ConsentimientoUsuario,
    EmailVerificationToken,
    IntentosFallidos,
    Login,
    RecoveryTokens,
    Register,
    RolPersonalizado,
)

logger = logging.getLogger(__name__)


class AuthRepository:
    def new_social_login_user(self):
        return Register()
    def save_user(self, user, fields=None):
        user.save(update_fields=fields) if fields else user.save()
        return user

    def save_social_login(self, sociallogin, request):
        return sociallogin.save(request)
    def get_active_patients_for_assignment(self):
        return list(Register.objects.filter(rol="paciente", activo=True).order_by("nombre").values(
            "idUsuario", "nombre", "email", "fotoPerfil"
        ))

    def get_verified_professionals_for_assignment(self):
        return list(Register.objects.filter(
            rol="profesional", activo=True, perfil_profesional__verificado=True
        ).annotate(
            pacientes=Count("pacientes_profesional", filter=Q(pacientes_profesional__idPaciente__isnull=False))
        ).order_by("nombre").values(
            "idUsuario", "nombre", "perfil_profesional__especialidad", "pacientes"
        ))

    def get_active_patient_for_assignment(self, patient_id):
        return Register.objects.filter(idUsuario=patient_id, rol="paciente", activo=True).first()

    def get_verified_professional_for_assignment(self, professional_id):
        return Register.objects.filter(
            idUsuario=professional_id, rol="profesional", activo=True,
            perfil_profesional__verificado=True,
        ).first()
    def get_registration_counts_by_day(self, start, end):
        return list(
            Register.objects.filter(fechaRegistro__gte=start, fechaRegistro__lt=end)
            .annotate(dia=TruncDate("fechaRegistro")).values("dia")
            .annotate(total=Count("pk"))
        )
    def get_custom_role_catalog(self):
        base_counts = dict(
            Register.objects.filter(rolPersonalizado__isnull=True)
            .values_list("rol")
            .annotate(n=Count("idUsuario"))
        )
        custom_roles = list(RolPersonalizado.objects.annotate(n=Count("usuarios")))
        return base_counts, custom_roles

    def custom_role_exists(self, name):
        return RolPersonalizado.objects.filter(nombre__iexact=name).exists()

    def create_custom_role(self, **data):
        return RolPersonalizado.objects.create(**data)

    def get_custom_role_for_deletion(self, role_id):
        return RolPersonalizado.objects.filter(idRol=role_id).annotate(n=Count("usuarios")).first()

    def delete_custom_role(self, role):
        return role.delete()

    def get_user_by_email_or_none(self, email):
        return Register.objects.filter(email__iexact=email).first()

    def get_user_by_name(self, name):
        return Register.objects.filter(nombre__icontains=name).first()

    def get_user_by_pk_or_none(self, user_id):
        return Register.objects.filter(pk=user_id).first()

    def get_user_contact_for_password_notice(self, user_id):
        return Register.objects.filter(idUsuario=user_id).first()

    def get_user_email(self, user_id):
        return Register.objects.filter(idUsuario=user_id).values_list("email", flat=True).first()

    def get_active_user_roles(self, user_ids):
        return dict(
            Register.objects.filter(
                idUsuario__in=user_ids, activo=True, estadoCuenta="Activa"
            ).values_list("idUsuario", "rol")
        )

    def list_pending_professionals(self):
        return list(
            Register.objects.filter(
                rol="profesional", perfil_profesional__verificado=False
            ).select_related("perfil_profesional").order_by("fechaRegistro")
        )

    def get_users_by_ids(self, user_ids):
        return {user.idUsuario: user for user in Register.objects.filter(idUsuario__in=user_ids)}

    def get_session_user(self, user_id):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            return User.objects.get(pk=user_id, activo=True, estadoCuenta="Activa")
        except User.DoesNotExist:
            return None

    def get_minor_candidates(self, active_only=True):
        qs = Register.objects.select_related("perfil_paciente").filter(
            perfil_paciente__fecha_nacimiento__isnull=False
        )
        if active_only:
            qs = qs.filter(activo=True, estadoCuenta="Activa")
        return qs

    def get_google_social_account(self, user):
        from allauth.socialaccount.models import SocialAccount
        try:
            return SocialAccount.objects.get(user=user, provider="google")
        except SocialAccount.DoesNotExist:
            return None

    def list_users_for_role_normalization(self):
        return Register.objects.all().only("idUsuario", "rol", "email", "nombre")

    def update_user_role(self, user_id, role):
        return Register.objects.filter(idUsuario=user_id).update(rol=role)

    def user_has_profile_photo(self, filename):
        return Register.objects.filter(fotoPerfil=filename).exists()

    def get_active_patient_user(self, user_id):
        return Register.objects.filter(
            idUsuario=user_id, rol="paciente", activo=True, estadoCuenta="Activa"
        ).first()

    def get_user_by_id_or_none(self, user_id):
        try:
            return Register.objects.get(idUsuario=user_id)
        except Register.DoesNotExist:
            return None

    def get_user_account_status(self, user_id):
        return Register.objects.only("activo", "estadoCuenta").get(pk=user_id)

    def get_user_account_status_or_none(self, user_id):
        return Register.objects.filter(pk=user_id).only("activo", "estadoCuenta").first()

    def get_user_by_pk(self, user_id):
        return Register.objects.get(pk=user_id)

    def get_user_by_email_for_auth(self, email):
        return Register.objects.get(email__iexact=email)

    def get_user_by_email_for_auth_or_none(self, email):
        return Register.objects.filter(email__iexact=email).first()

    def get_user_by_id_with_role(self, user_id):
        return Register.objects.filter(idUsuario=user_id).select_related("rolPersonalizado").first()

    def user_exists_by_email(self, email):
        return Register.objects.filter(email__iexact=email).exists()

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
        qs = Register.objects.filter(email__iexact=email, estadoCuenta="Activa")
        if admin_only:
            qs = qs.filter(rol="admin")
        user = qs.first()
        if user:
            return user.to_dict()
        return None

    def get_user_by_id(self, user_id):
        """Usuario por id (con su rol personalizado), o None si no existe."""
        return Register.objects.select_related("rolPersonalizado").filter(idUsuario=user_id).first()

    def estado_cuenta(self, user_id):
        """(activo, estadoCuenta) del usuario, o None si no existe. Solo lee esas dos columnas."""
        return Register.objects.filter(pk=user_id).values_list("activo", "estadoCuenta").first()

    def registrar_consentimiento(self, user_id, tipo, version, ip, user_agent):
        return ConsentimientoUsuario.objects.create(
            idUsuario_id=user_id,
            tipo=tipo,
            version=version,
            aceptado=True,
            ip=ip,
            userAgent=user_agent,
        )

    def active_user_exists_by_email(self, email):
        return Register.objects.filter(
            email=email, estadoCuenta="Activa"
        ).exists()

    def create_password_recovery_token(self, email, token, expires):
        user = Register.objects.filter(email__iexact=email).first()
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
    def persist_totp_device(self, device):
        device.save()
        return device

    def delete_totp_device(self, device):
        return device.delete()
    def check_brute_force(self, email):
        try:
            row = IntentosFallidos.objects.filter(email__iexact=email).first()
            if not row:
                return False, 0
            from apps.admin_panel.seguridad import bloqueo
            intentos_maximos, _ = bloqueo()
            if row.intentos < intentos_maximos:
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
            row = IntentosFallidos.objects.filter(email__iexact=email).first()
            if row:
                row.intentos += 1
                row.ultimo_intento = now
                from apps.admin_panel.seguridad import bloqueo
                intentos_maximos, minutos_bloqueo = bloqueo()
                if row.intentos >= intentos_maximos:
                    row.bloqueado_hasta = now + timedelta(minutes=minutos_bloqueo)
                row.save(update_fields=["intentos", "ultimo_intento", "bloqueado_hasta"])
            else:
                IntentosFallidos.objects.create(
                    email=email, intentos=1, ultimo_intento=now
                )
        except Exception:
            return

    def reset_failed_attempts(self, email):
        try:
            row = IntentosFallidos.objects.filter(email__iexact=email).first()
            if row:
                row.intentos = 0
                row.bloqueado_hasta = None
                row.save(update_fields=["intentos", "bloqueado_hasta"])
        except Exception:
            return

    def check_rate_limit(self, key, max_attempts=10, window_minutes=60, lockout_minutes=30):
        try:
            row = IntentosFallidos.objects.filter(email__iexact=key).first()
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
            row = IntentosFallidos.objects.filter(email__iexact=key).first()
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
            row = IntentosFallidos.objects.filter(email__iexact=key).first()
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
