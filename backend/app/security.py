import hashlib
import secrets
import hmac

from app.config import settings
from app.errors import AppError
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()

DUMMY_PASSWORD_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hasher.verify(password, encoded_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def new_email_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"

def password_reset_digest(purpose: str, value: str) -> str:
    secret = settings.password_reset_secret
    if len(secret) < 32:
        raise AppError(
            "PASSWORD_RESET_NOT_CONFIGURED",
            "La recuperación de contraseña no está configurada.",
        )

    return hmac.new(
        secret.encode("utf-8"),
        f"{purpose}\0{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
