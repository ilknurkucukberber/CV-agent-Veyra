import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base, import_models
from app.db.session import get_db
from app.main import app

import_models()

# Test paketi tek bir istemci "IP"sinden onlarca kez register/login yapar;
# üretimdeki brute-force koruması bu ortamda anlamsız, bu yüzden kapatılır.
settings.RATE_LIMIT_ENABLED = False

# Geliştirme veritabanına dokunmamak için ayrı test veritabanı kullanılır.
TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/cvagent_test"

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Test şemasını sıfırdan kurar (enum tipleri dahil)."""
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def isolate_transactional_email(monkeypatch):
    """API tests must not send real email; delivery is tested separately."""
    monkeypatch.setattr("app.api.routes.auth.ensure_email_configured", lambda: None)
    monkeypatch.setattr("app.api.routes.auth.send_verification_email", lambda *args: None)
    monkeypatch.setattr("app.api.routes.auth.send_password_reset_email", lambda *args: None)
    monkeypatch.setattr("app.workers.tasks.send_reminder_digest", lambda *args: None)


@pytest.fixture(autouse=True)
def isolate_parse_provider_configuration(monkeypatch):
    """Pipeline/API tests mock the model; no live provider key is needed."""
    monkeypatch.setattr("app.api.routes.resumes.ensure_configured", lambda: "groq")


@pytest.fixture(autouse=True)
def prevent_live_model_requests(monkeypatch):
    """Tests must explicitly supply a model response, never use local API keys."""
    def unexpected_request(*args, **kwargs):
        raise AssertionError("Model response must be mocked in tests")

    monkeypatch.setattr("app.core.llm.parse_structured", unexpected_request)


@pytest.fixture(autouse=True)
def clean_tables():
    """Her testten sonra tabloları boşaltarak izolasyon sağlar."""
    yield
    with engine.connect() as conn:
        table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
        conn.commit()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def user_credentials() -> dict[str, str]:
    return {"email": "test@example.com", "password": "sifre1234"}


@pytest.fixture()
def auth_headers(client: TestClient, user_credentials: dict[str, str]) -> dict[str, str]:
    from tests.fixtures import register_and_login

    token = register_and_login(client, user_credentials)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def isolated_pipeline(monkeypatch, tmp_path):
    """CV parse task'ını test DB'sine ve geçici storage'a yönlendirir;
    Celery'yi senkronlaştırır."""
    import app.workers.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("app.core.config.settings.STORAGE_DIR", str(tmp_path))

    class SyncTask:
        @staticmethod
        def delay(resume_id: int):
            tasks_module.run_resume_parse(resume_id)

    monkeypatch.setattr("app.api.routes.resumes.parse_resume_task", SyncTask)


@pytest.fixture()
def mock_llm(monkeypatch):
    """CV parse LLM çağrısını sabit fixture'la değiştirir."""
    import app.workers.tasks as tasks_module
    from tests.fixtures import FAKE_PARSED

    monkeypatch.setattr(tasks_module, "parse_resume_text", lambda text: FAKE_PARSED)
