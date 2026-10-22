import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt yalnızca ilk 72 baytı işler; bunun ötesi sessizce yok sayılır. Bu,
# passlib'in de tarihsel olarak yaptığı şeydir — mevcut hash'lerle uyumluluğu
# bozmamak için aynı davranış korunuyor.
BCRYPT_MAX_PASSWORD_BYTES = 72

OPAQUE_TOKEN_BYTES = 32
PASSWORD_RESET_TOKEN_TTL_MINUTES = 30
EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 24


def generate_opaque_token(ttl: timedelta) -> tuple[str, str, datetime]:
    """Ham token (kullanıcıya gönderilir) ve hash'ini (DB'de saklanır) üretir.

    Şifre sıfırlama ve e-posta doğrulama gibi tek kullanımlık, süreli
    linkler için ortak üretici. Ham token asla veritabanına yazılmaz;
    yalnızca SHA-256 hash'i saklanır, böylece DB sızıntısında tokenlar
    tekrar kullanılabilir hale gelmez.
    """
    raw_token = secrets.token_urlsafe(OPAQUE_TOKEN_BYTES)
    token_hash = hash_opaque_token(raw_token)
    expires_at = datetime.now(timezone.utc) + ttl
    return raw_token, token_hash, expires_at


def generate_password_reset_token() -> tuple[str, str, datetime]:
    return generate_opaque_token(timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES))


def generate_email_verification_token() -> tuple[str, str, datetime]:
    return generate_opaque_token(timedelta(hours=EMAIL_VERIFICATION_TOKEN_TTL_HOURS))


def hash_opaque_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    truncated = plain_password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(truncated, hashed_password.encode("utf-8"))
    except ValueError:
        # Bozuk/tanınmayan bir hash formatı; asla eşleşme kabul etme.
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
