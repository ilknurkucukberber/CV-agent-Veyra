import io

import pytest
from fastapi.testclient import TestClient

import app.workers.tasks as tasks_module
from tests.fixtures import make_pdf_bytes, register_and_login, upload_pdf


class TestUpload:
    def test_missing_ai_configuration_is_reported_before_saving(
        self, client, auth_headers, monkeypatch
    ):
        from app.core.llm import LLMConfigurationError

        def missing():
            raise LLMConfigurationError("Yapay zekâ servisi yapılandırılmamış.")

        monkeypatch.setattr("app.api.routes.resumes.ensure_configured", missing)
        response = upload_pdf(client, auth_headers)
        assert response.status_code == 503
        assert "yapılandırılmamış" in response.json()["detail"]
        assert client.get("/api/v1/resumes", headers=auth_headers).json() == []

    def test_upload_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/v1/resumes/upload",
            files={"file": ("cv.pdf", io.BytesIO(b"x"), "application/pdf")},
        )
        assert resp.status_code == 401

    def test_upload_rejects_unsupported_type(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        resp = client.post(
            "/api/v1/resumes/upload",
            files={"file": ("cv.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_upload_rejects_empty_file(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        resp = client.post(
            "/api/v1/resumes/upload",
            files={"file": ("cv.pdf", io.BytesIO(b""), "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_upload_pdf_success(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        resp = upload_pdf(client, auth_headers)
        assert resp.status_code == 202, resp.text
        body = resp.json()
        assert body["original_filename"] == "cv.pdf"
        assert body["content_type"] == "application/pdf"


class TestParsePipeline:
    def test_failed_resume_can_be_reprocessed_in_place(self, client, auth_headers, monkeypatch):
        from tests.fixtures import FAKE_PARSED

        def fail(text):
            raise RuntimeError("Provider failure")

        monkeypatch.setattr(tasks_module, "parse_resume_text", fail)
        resume_id = upload_pdf(client, auth_headers).json()["id"]
        monkeypatch.setattr(tasks_module, "parse_resume_text", lambda text: FAKE_PARSED)
        response = client.post(f"/api/v1/resumes/{resume_id}/retry-parse", headers=auth_headers)
        assert response.status_code == 202
        status = client.get(f"/api/v1/resumes/{resume_id}/status", headers=auth_headers).json()
        assert status["parse_status"] == "completed"
        assert status["parse_error"] is None
        assert len(client.get("/api/v1/resumes", headers=auth_headers).json()) == 1

    def test_completed_resume_cannot_be_requeued(self, client, auth_headers, mock_llm):
        resume_id = upload_pdf(client, auth_headers).json()["id"]
        assert client.post(f"/api/v1/resumes/{resume_id}/retry-parse", headers=auth_headers).status_code == 409

    def test_end_to_end_pdf_parse(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]

        status_resp = client.get(
            f"/api/v1/resumes/{resume_id}/status", headers=auth_headers
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["parse_status"] == "completed"

        detail = client.get(f"/api/v1/resumes/{resume_id}", headers=auth_headers).json()
        assert detail["parsed_json"]["personal_info"]["email"] == "arda.yilmaz@example.com"
        assert detail["parsed_json"]["skills"] == [
            "Python", "FastAPI", "PostgreSQL", "Docker", "Git",
        ]
        assert detail["page_count"] == 1

        analysis = detail["structure_analysis"]
        assert analysis["has_email"] is True
        assert analysis["has_phone"] is True
        assert analysis["too_long"] is False
        assert "education" in analysis["detected_sections"]
        assert "experience" in analysis["detected_sections"]

    def test_llm_failure_marks_failed(
        self, client: TestClient, auth_headers: dict[str, str], monkeypatch
    ):
        def boom(text: str):
            raise RuntimeError("LLM patladı")

        monkeypatch.setattr(tasks_module, "parse_resume_text", boom)
        resume_id = upload_pdf(client, auth_headers).json()["id"]

        body = client.get(
            f"/api/v1/resumes/{resume_id}/status", headers=auth_headers
        ).json()
        assert body["parse_status"] == "failed"
        assert "beklenmeyen bir hata" in body["parse_error"]

    def test_image_upload_fails_with_ocr_placeholder_message(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        resp = client.post(
            "/api/v1/resumes/upload",
            files={"file": ("cv.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 202
        body = client.get(
            f"/api/v1/resumes/{resp.json()['id']}/status", headers=auth_headers
        ).json()
        assert body["parse_status"] == "failed"
        assert "OCR" in body["parse_error"]


class TestStatusAccess:
    def test_status_not_found(self, client: TestClient, auth_headers: dict[str, str]):
        resp = client.get("/api/v1/resumes/9999/status", headers=auth_headers)
        assert resp.status_code == 404

    def test_cannot_see_other_users_resume(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]

        other = {"email": "other@example.com", "password": "sifre1234"}
        token = register_and_login(client, other)
        resp = client.get(
            f"/api/v1/resumes/{resume_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestListDeleteAndPrimary:
    def test_list_is_empty_then_reflects_uploads(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        assert client.get("/api/v1/resumes", headers=auth_headers).json() == []

        upload_pdf(client, auth_headers, filename="a.pdf")
        upload_pdf(client, auth_headers, filename="b.pdf")

        listing = client.get("/api/v1/resumes", headers=auth_headers).json()
        assert len(listing) == 2
        assert {r["original_filename"] for r in listing} == {"a.pdf", "b.pdf"}

    def test_list_only_returns_own_resumes(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        upload_pdf(client, auth_headers)

        other = {"email": "other@example.com", "password": "sifre1234"}
        other_token = register_and_login(client, other)
        other_headers = {"Authorization": f"Bearer {other_token}"}

        assert client.get("/api/v1/resumes", headers=other_headers).json() == []
        assert len(client.get("/api/v1/resumes", headers=auth_headers).json()) == 1

    def test_set_primary_unsets_previous_primary(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        first_id = upload_pdf(client, auth_headers, filename="a.pdf").json()["id"]
        second_id = upload_pdf(client, auth_headers, filename="b.pdf").json()["id"]

        resp = client.patch(
            f"/api/v1/resumes/{first_id}", json={"is_primary": True}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_primary"] is True

        resp = client.patch(
            f"/api/v1/resumes/{second_id}", json={"is_primary": True}, headers=auth_headers
        )
        assert resp.json()["is_primary"] is True

        listing = {r["id"]: r["is_primary"] for r in client.get("/api/v1/resumes", headers=auth_headers).json()}
        assert listing[first_id] is False
        assert listing[second_id] is True

    def test_delete_removes_resume_and_404s_after(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]

        resp = client.delete(f"/api/v1/resumes/{resume_id}", headers=auth_headers)
        assert resp.status_code == 204

        assert client.get(f"/api/v1/resumes/{resume_id}", headers=auth_headers).status_code == 404
        assert client.get("/api/v1/resumes", headers=auth_headers).json() == []

    def test_cannot_delete_other_users_resume(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]

        other = {"email": "other@example.com", "password": "sifre1234"}
        other_token = register_and_login(client, other)
        resp = client.delete(
            f"/api/v1/resumes/{resume_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 404
        # Ve gerçekten silinmemiş olmalı:
        assert client.get(f"/api/v1/resumes/{resume_id}", headers=auth_headers).status_code == 200


class TestResumeShare:
    def test_no_share_initially(self, client: TestClient, auth_headers: dict[str, str], mock_llm):
        resume_id = upload_pdf(client, auth_headers).json()["id"]
        resp = client.get(f"/api/v1/resumes/{resume_id}/share", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_create_share_is_idempotent(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]

        first = client.post(f"/api/v1/resumes/{resume_id}/share", headers=auth_headers)
        assert first.status_code == 201
        second = client.post(f"/api/v1/resumes/{resume_id}/share", headers=auth_headers)
        assert second.status_code == 201
        assert first.json()["token"] == second.json()["token"]

    def test_public_view_requires_no_auth_and_includes_latest_analysis(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm, monkeypatch
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]
        token = client.post(f"/api/v1/resumes/{resume_id}/share", headers=auth_headers).json()["token"]

        # Kimlik doğrulama başlığı OLMADAN çağrılıyor — bu uç girişsiz olmalı.
        resp = client.get(f"/api/v1/share/resumes/{token}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["parsed_json"]["skills"] == ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"]
        assert body["latest_ats_analysis"] is None

    def test_revoke_makes_link_404(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]
        token = client.post(f"/api/v1/resumes/{resume_id}/share", headers=auth_headers).json()["token"]

        resp = client.delete(f"/api/v1/resumes/{resume_id}/share", headers=auth_headers)
        assert resp.status_code == 204

        assert client.get(f"/api/v1/share/resumes/{token}").status_code == 404

    def test_unknown_token_404s(self, client: TestClient):
        resp = client.get("/api/v1/share/resumes/not-a-real-token")
        assert resp.status_code == 404

    def test_only_owner_can_create_share(
        self, client: TestClient, auth_headers: dict[str, str], mock_llm
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]

        other = {"email": "other@example.com", "password": "sifre1234"}
        other_token = register_and_login(client, other)
        resp = client.post(
            f"/api/v1/resumes/{resume_id}/share",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 404
