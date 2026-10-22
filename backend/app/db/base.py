from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Tüm ORM modellerinin miras alacağı taban sınıf."""


def import_models() -> None:
    """Alembic autogenerate'in tüm modelleri görebilmesi için import eder."""
    import app.models  # noqa: F401
