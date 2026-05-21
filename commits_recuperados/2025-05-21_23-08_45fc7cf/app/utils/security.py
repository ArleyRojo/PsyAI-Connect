import hashlib


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def is_sha256_hash(text: str) -> bool:
    return len(text) == 64 and all(c in '0123456789abcdef' for c in text)


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        if is_sha256_hash(hashed):
            return hashlib.sha256(password.encode()).hexdigest() == hashed
    except Exception:
        pass
    return False