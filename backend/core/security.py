"""Password hashing (stdlib only) and anonymous lead ids."""

import hashlib
import hmac
import secrets

from core.config import settings


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), settings.pbkdf2_iterations
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), stored)


def new_anon_id(existing: set[str]) -> str:
    while True:
        candidate = f"ANON-{secrets.token_hex(3).upper()}"
        if candidate not in existing:
            return candidate
