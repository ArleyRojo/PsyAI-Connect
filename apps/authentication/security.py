import hashlib

import bcrypt


class SecurityHelper:
    @staticmethod
    def _sha256(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def hash_password(password: str) -> str:
        return SecurityHelper._sha256(password)

    @staticmethod
    def is_sha256_hash(text: str) -> bool:
        return len(text) == 64 and all(c in "0123456789abcdef" for c in text)

    @staticmethod
    def _is_bcrypt(hash_str: str) -> bool:
        return (
            hash_str.startswith("$2b$")
            or hash_str.startswith("$2a$")
            or hash_str.startswith("$2y$")
        )

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        if not hashed:
            return False
        try:
            if SecurityHelper.is_sha256_hash(hashed):
                return SecurityHelper._sha256(password) == hashed
            if SecurityHelper._is_bcrypt(hashed):
                if bcrypt.checkpw(
                    SecurityHelper._sha256(password).encode(),
                    hashed.encode("utf-8"),
                ):
                    return True
                return bcrypt.checkpw(
                    password.encode(), hashed.encode("utf-8")
                )
            from django.contrib.auth.hashers import check_password as django_check
            sha = SecurityHelper._sha256(password)
            if django_check(sha, hashed):
                return True
            return django_check(password, hashed)
        except Exception:
            pass
        return False
