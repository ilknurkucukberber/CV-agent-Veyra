from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.rate_limit import rate_limiter
from app.core.security import (
    create_access_token,
    generate_email_verification_token,
    generate_password_reset_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.models import EmailVerificationToken, PasswordResetToken, User
from app.schemas.auth import (
    EmailVerificationConfirm,
    PasswordResetConfirm,
    PasswordResetRequest,
    ResendVerificationRequest,
    Token,
    UserLogin,
)
from app.schemas.user import UserCreate, UserResponse
from app.services.email import (
    EmailDeliveryError,
    ensure_email_configured,
    send_password_reset_email,
    send_verification_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# IP başına: 5 kayıt/saat, 10 giriş denemesi/5dk, 5 sıfırlama isteği/saat,
# 10 sıfırlama onayı/saat (token zaten 32 bayt rastgele olduğundan brute-force
# pratik değil, ama yine de savunma katmanı olarak sınırlandırılıyor).
_register_limit = Depends(rate_limiter("register", max_requests=5, window_seconds=3600))
_login_limit = Depends(rate_limiter("login", max_requests=10, window_seconds=300))
_reset_request_limit = Depends(rate_limiter("password-reset-request", max_requests=5, window_seconds=3600))
_reset_confirm_limit = Depends(rate_limiter("password-reset-confirm", max_requests=10, window_seconds=3600))
_verify_limit = Depends(rate_limiter("verify-email", max_requests=10, window_seconds=3600))
_resend_verify_limit = Depends(rate_limiter("resend-verification", max_requests=5, window_seconds=3600))

GENERIC_RESET_REQUEST_MESSAGE = (
    "İsteğin alındı. Bu adresle aktif bir hesap varsa şifre sıfırlama e-postası gönderimi denenir."
)
GENERIC_RESEND_VERIFICATION_MESSAGE = (
    "İsteğin alındı. Bu adresle aktif ve doğrulanmamış bir hesap varsa doğrulama e-postası gönderimi denenir."
)


def _issue_verification_email(db: DbSession, user: User) -> None:
    raw_token, token_hash, expires_at = generate_email_verification_token()
    db.add(
        EmailVerificationToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
    )
    db.commit()
    verify_url = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/verify-email?token={raw_token}"
    send_verification_email(user.email, verify_url)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_register_limit],
)
def register(payload: UserCreate, db: DbSession) -> User:
    ensure_email_configured()
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresi zaten kayıtlı",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    try:
        _issue_verification_email(db, user)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=503,
            detail="Hesabın oluşturuldu ancak doğrulama e-postası gönderilemedi. Giriş sayfasından doğrulama linkini tekrar göndermeyi deneyebilirsin.",
        ) from exc
    return user


@router.post("/login", response_model=Token, dependencies=[_login_limit])
def login(payload: UserLogin, db: DbSession) -> Token:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya parola hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hesap devre dışı",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="E-posta adresin henüz doğrulanmadı. Doğrulama linki için gelen kutunu kontrol et.",
        )
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> User:
    return current_user


@router.post(
    "/password-reset/request",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[_reset_request_limit],
)
def request_password_reset(payload: PasswordResetRequest, db: DbSession) -> dict[str, str]:
    """Şifre sıfırlama linki üretir.

    Güvenlik: e-posta sistemde kayıtlı olsun ya da olmasın AYNI genel mesaj
    dönülür; böylece bu uçtan hangi e-postaların kayıtlı olduğu enumerate
    edilemez (user enumeration önlenir).
    """
    ensure_email_configured()
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is not None and user.is_active:
        raw_token, token_hash, expires_at = generate_password_reset_token()
        db.add(
            PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        )
        db.commit()
        reset_url = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/reset-password?token={raw_token}"
        try:
            send_password_reset_email(user.email, reset_url)
        except EmailDeliveryError:
            logger.error("Password reset email delivery failed")

    return {"message": GENERIC_RESET_REQUEST_MESSAGE}


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_200_OK,
    dependencies=[_reset_confirm_limit],
)
def confirm_password_reset(payload: PasswordResetConfirm, db: DbSession) -> dict[str, str]:
    token_hash = hash_opaque_token(payload.token)
    reset_token = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    if (
        reset_token is None
        or reset_token.used_at is not None
        or reset_token.expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sıfırlama linki geçersiz veya süresi dolmuş. Lütfen yeni bir link isteyin.",
        )

    user = db.get(User, reset_token.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sıfırlama linki geçersiz veya süresi dolmuş. Lütfen yeni bir link isteyin.",
        )

    user.hashed_password = hash_password(payload.new_password)
    reset_token.used_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Şifreniz güncellendi. Yeni şifrenizle giriş yapabilirsiniz."}


@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    dependencies=[_verify_limit],
)
def verify_email(payload: EmailVerificationConfirm, db: DbSession) -> dict[str, str]:
    token_hash = hash_opaque_token(payload.token)
    verification = db.scalar(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    )
    if (
        verification is None
        or verification.used_at is not None
        or verification.expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doğrulama linki geçersiz veya süresi dolmuş. Yeni bir link isteyebilirsin.",
        )

    user = db.get(User, verification.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doğrulama linki geçersiz veya süresi dolmuş. Yeni bir link isteyebilirsin.",
        )

    user.is_verified = True
    verification.used_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "E-posta adresin doğrulandı. Artık giriş yapabilirsin."}


@router.post(
    "/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[_resend_verify_limit],
)
def resend_verification(payload: ResendVerificationRequest, db: DbSession) -> dict[str, str]:
    """Aynı genel mesajı döner (user enumeration önlemi, bkz. request_password_reset)."""
    ensure_email_configured()
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is not None and user.is_active and not user.is_verified:
        try:
            _issue_verification_email(db, user)
        except EmailDeliveryError:
            logger.error("Verification email redelivery failed")

    return {"message": GENERIC_RESEND_VERIFICATION_MESSAGE}
