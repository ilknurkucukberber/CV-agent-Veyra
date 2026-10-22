from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "CV Agent API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://cvagent:cvagent@localhost:5432/cvagent"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Auth
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # LLM
    # LLM_PROVIDER: "auto" | "anthropic" | "gemini" | "groq" — "auto" iken
    # tanımlı olan ilk anahtara göre şu öncelikle seçilir: anthropic > gemini > groq.
    LLM_PROVIDER: str = "auto"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-opus-5"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Storage ("local" | "s3")
    STORAGE_BACKEND: str = "local"
    STORAGE_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 10
    
    # S3 Storage Configuration
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-central-1"
    AWS_BUCKET_NAME: str = ""
    AWS_ENDPOINT_URL: str | None = None  # Use for Cloudflare R2, MinIO, etc.

    # SMTP Configuration
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Veyra"
    SMTP_USE_SSL: bool = False
    SMTP_USE_TLS: bool = True
    SMTP_TIMEOUT_SECONDS: float = 15.0

    # İlan URL'den içerik çekme
    # Boş bırakılırsa tüm public adreslere izin verilir (özel/yerel ağlar her
    # durumda engellenir). Virgülle ayrılmış alan adı listesiyle daraltılabilir.
    ALLOWED_JOB_DOMAINS: str = ""
    FETCH_TIMEOUT_SECONDS: float = 10.0
    MAX_FETCH_KB: int = 512

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # Hız sınırlama (bkz. app/core/rate_limit.py). Test paketi tek bir "IP"den
    # onlarca kullanıcı kaydı/girişi yaptığından test ortamında kapatılır
    # (bkz. tests/conftest.py).
    RATE_LIMIT_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
