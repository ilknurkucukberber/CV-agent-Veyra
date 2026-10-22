"""Create a verified demo account from the local development terminal only."""
import argparse
import getpass
import sys
from urllib.parse import urlsplit

DEMO_EMAIL = "demo@example.com"
DEMO_NAME = "Veyra Yerel Test"


def require_local_development(environment: str, frontend_origin: str) -> None:
    if environment != "development" or urlsplit(frontend_origin).hostname not in {
        "localhost", "127.0.0.1", "::1",
    }:
        raise ValueError("Test hesabı yalnızca localhost geliştirme ortamında oluşturulabilir.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Veyra yerel test hesabı oluştur")
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()

    from app.core.config import settings

    try:
        require_local_development(settings.ENVIRONMENT, settings.FRONTEND_ORIGIN)
        password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else getpass.getpass("Test hesabı şifresi: ")
        if len(password) < 8 or len(password.encode("utf-8")) > 72:
            raise ValueError("Test şifresi en az 8 karakter ve en fazla 72 bayt olmalıdır.")

        from sqlalchemy import select
        from app.core.security import hash_password, verify_password
        from app.db.session import SessionLocal
        from app.models import User

        with SessionLocal() as db:
            existing = db.scalar(select(User).where(User.email == DEMO_EMAIL))
            if existing:
                if not (existing.full_name == DEMO_NAME and existing.is_verified
                        and existing.is_active and verify_password(password, existing.hashed_password)):
                    raise ValueError("Bu adreste farklı bir hesap zaten var; mevcut hesap değiştirilmedi.")
                print(f"Yerel test hesabı kullanıma hazır: {DEMO_EMAIL}")
                return 0
            db.add(User(email=DEMO_EMAIL, full_name=DEMO_NAME,
                        hashed_password=hash_password(password), is_active=True, is_verified=True))
            db.commit()
        print(f"Doğrulanmış yerel test hesabı oluşturuldu: {DEMO_EMAIL}")
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
