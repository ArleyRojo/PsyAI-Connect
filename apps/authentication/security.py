import hashlib
import hmac
import re

from django.conf import settings
from django.contrib.auth.hashers import check_password, identify_hasher, make_password

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SecurityHelper:
    @staticmethod
    def hash_password(password: str) -> str:
        """Todo hash nuevo se genera con Argon2id."""
        return make_password(password)

    @staticmethod
    def is_legacy_sha256(hashed: str) -> bool:
        return bool(hashed) and bool(_SHA256_RE.match(hashed))

    @staticmethod
    def is_django_hash(hashed: str) -> bool:
        try:
            identify_hasher(hashed)
            return True
        except ValueError:
            return False

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Detecta el formato del hash guardado y verifica según corresponda."""
        if not hashed:
            return False

        # Cuentas existentes: SHA-256 en hex (64 caracteres)
        if SecurityHelper.is_legacy_sha256(hashed):
            return hmac.compare_digest(
                hashlib.sha256(password.encode()).hexdigest(), hashed
            )

        # Cuentas nuevas: Argon2id (también PBKDF2 / bcrypt de Django)
        if SecurityHelper.is_django_hash(hashed):
            try:
                return check_password(password, hashed)
            except Exception:
                return False

        # Texto plano: solo para bootstrap directo en MySQL, apagado por defecto
        if getattr(settings, "ALLOW_PLAINTEXT_BOOTSTRAP", False):
            return hmac.compare_digest(password, hashed)

        return False

    @staticmethod
    def needs_upgrade(hashed: str) -> bool:
        """
        True solo para texto plano (bootstrap), que debe convertirse a Argon2id.
        Los hashes SHA-256 existentes NO se tocan.
        """
        return (
            bool(hashed)
            and not SecurityHelper.is_legacy_sha256(hashed)
            and not SecurityHelper.is_django_hash(hashed)
        )
