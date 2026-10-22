import pytest
from fastapi.testclient import TestClient

from app.agents.cv_writer import (
    ChangeLogEntry,
    RewriteResult,
    RewrittenResume,
)
from tests.fixtures import FAKE_PARSED, upload_pdf

FAKE_REWRITE = RewriteResult(
    updated_content=RewrittenResume(
        **{
            **FAKE_PARSED.model_dump(),
            "experience": [
                {
                    **FAKE_PARSED.experience[0].model_dump(),
                    "description": (
                        "FastAPI ile RESTful mikroservisler geliştirdim; PostgreSQL "
                        "sorgularını optimize ettim."
                    ),
                }
            ],
        },
        summary=None,
    ),
    change_log=[
        ChangeLogEntry(
            section="experience[0].description",
            before="Python ve FastAPI ile mikroservis geliştirme.",
            after=(
                "FastAPI ile RESTful mikroservisler geliştirdim; PostgreSQL "
                "sorgularını optimize ettim."
            ),
            reason="İlandaki 'RESTful API' anahtar kelimesi mevcut FastAPI deneyimine doğal biçimde yerleştirildi.",
        )
    ],
)

JOB_PAYLOAD = {
    "title": "Backend Developer",
    "company": "TechCo",
    "description": "RESTful API geliştirme, PostgreSQL, Docker deneyimi aranıyor.",
    "requirements": ["Python", "RESTful API", "PostgreSQL", "Docker"],
}


@pytest.fixture()
def mock_writer(monkeypatch):
    calls: list[dict] = []

    def fake(edit_level, source_content, profile=None, job_posting=None, language="tr"):
        calls.append(
            {
                "edit_level": edit_level,
                "source_content": source_content,
                # ORM nesneleri istek oturumu kapanınca detach olur; değerleri kopyala
                "profile": None if profile is None else {"id": profile.id},
                "job_posting_title": None if job_posting is None else job_posting.title,
            }
        )
        return FAKE_REWRITE.model_copy(deep=True)

    monkeypatch.setattr("app.api.routes.resumes.rewrite_resume", fake)
    return calls


@pytest.fixture()
def resume_id(client: TestClient, auth_headers, mock_llm) -> int:
    return upload_pdf(client, auth_headers).json()["id"]


def create_job(client: TestClient, headers) -> int:
    # job_postings için henüz endpoint yok; testte doğrudan DB'ye yazıyoruz.
    from app.models import JobPosting, User
    from sqlalchemy import select
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "test@example.com"))
        job = JobPosting(user_id=user.id, **JOB_PAYLOAD)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job.id
    finally:
        db.close()


class TestRewriteEndpoint:
    def test_requires_auth(self, client: TestClient):
        resp = client.post("/api/v1/resumes/1/rewrite", json={"edit_level": "light"})
        assert resp.status_code == 401

    def test_resume_not_found(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/v1/resumes/9999/rewrite",
            json={"edit_level": "light"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_invalid_edit_level(self, client: TestClient, auth_headers, resume_id):
        resp = client.post(
            f"/api/v1/resumes/{resume_id}/rewrite",
            json={"edit_level": "mega"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_targeted_requires_job_posting(
        self, client: TestClient, auth_headers, resume_id, mock_writer
    ):
        resp = client.post(
            f"/api/v1/resumes/{resume_id}/rewrite",
            json={"edit_level": "targeted"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_targeted_unknown_job_404(
        self, client: TestClient, auth_headers, resume_id, mock_writer
    ):
        resp = client.post(
            f"/api/v1/resumes/{resume_id}/rewrite",
            json={"edit_level": "targeted", "target_job_posting_id": 777},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_light_rewrite_creates_version(
        self, client: TestClient, auth_headers, resume_id, mock_writer
    ):
        resp = client.post(
            f"/api/v1/resumes/{resume_id}/rewrite",
            json={"edit_level": "light"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["version_number"] == 1
        assert body["edit_level"] == "light"
        assert body["content"]["personal_info"]["name"] == "Arda Yılmaz"
        assert body["change_log"][0]["reason"]
        # light modda ilan/profil gönderilmemeli
        assert mock_writer[0]["job_posting_title"] is None
        assert mock_writer[0]["profile"] is None

    def test_targeted_passes_job_and_increments_version(
        self, client: TestClient, auth_headers, resume_id, mock_writer
    ):
        job_id = create_job(client, auth_headers)

        first = client.post(
            f"/api/v1/resumes/{resume_id}/rewrite",
            json={"edit_level": "light"},
            headers=auth_headers,
        ).json()
        second = client.post(
            f"/api/v1/resumes/{resume_id}/rewrite",
            json={"edit_level": "targeted", "target_job_posting_id": job_id},
            headers=auth_headers,
        ).json()

        assert first["version_number"] == 1
        assert second["version_number"] == 2
        assert second["job_posting_id"] == job_id
        assert mock_writer[1]["job_posting_title"] == "Backend Developer"
        # İkinci çağrının kaynağı ilk versiyonun içeriği olmalı (zincirleme)
        assert (
            mock_writer[1]["source_content"]["experience"][0]["description"]
            == FAKE_REWRITE.updated_content.experience[0].description
        )

    def test_old_versions_preserved(
        self, client: TestClient, auth_headers, resume_id, mock_writer
    ):
        for _ in range(3):
            client.post(
                f"/api/v1/resumes/{resume_id}/rewrite",
                json={"edit_level": "light"},
                headers=auth_headers,
            )
        versions = client.get(
            f"/api/v1/resumes/{resume_id}/versions", headers=auth_headers
        ).json()
        assert [v["version_number"] for v in versions] == [3, 2, 1]


class TestVersionEndpoints:
    def test_versions_requires_auth(self, client: TestClient):
        assert client.get("/api/v1/resumes/1/versions").status_code == 401

    def test_patch_version_content(
        self, client: TestClient, auth_headers, resume_id, mock_writer
    ):
        version = client.post(
            f"/api/v1/resumes/{resume_id}/rewrite",
            json={"edit_level": "light"},
            headers=auth_headers,
        ).json()

        edited = dict(version["content"])
        edited["skills"] = ["Python", "FastAPI"]
        resp = client.patch(
            f"/api/v1/resumes/{resume_id}/versions/{version['id']}",
            json={"content": edited, "change_summary": "Kullanıcı düzenlemesi"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"]["skills"] == ["Python", "FastAPI"]
        assert resp.json()["change_summary"] == "Kullanıcı düzenlemesi"

    def test_patch_unknown_version_404(
        self, client: TestClient, auth_headers, resume_id
    ):
        resp = client.patch(
            f"/api/v1/resumes/{resume_id}/versions/999",
            json={"change_summary": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
