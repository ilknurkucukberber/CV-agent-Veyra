import pytest
from fastapi.testclient import TestClient

from app.agents.ats_analyzer import DISCLAIMER, _clamp_and_reconcile
from app.agents.ats_schema import (
    CATEGORY_WEIGHTS,
    AtsAnalysisResult,
    AtsGap,
    CategoryScores,
)
from tests.fixtures import upload_pdf

FAKE_RESULT = AtsAnalysisResult(
    total_score=76,
    category_scores=CategoryScores(
        format_readability=12,
        contact_info=10,
        experience_quality=14,
        technical_skills=12,
        keyword_match=13,
        projects_achievements=11,
        language_quality=4,
    ),
    strengths=["Teknik beceriler net listelenmiş", "İletişim bilgileri eksiksiz"],
    gaps=[
        AtsGap(
            issue="Deneyim maddelerinde ölçülebilir sonuç yok",
            why_it_matters="ATS ve işe alım uzmanları somut etki arar.",
            how_to_fix="Her maddeye sayısal sonuç ekleyin (ör. '%30 hızlandırdım').",
        )
    ],
)


@pytest.fixture()
def mock_ats(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.resumes.analyze_resume",
        lambda parsed, structure, job=None, language="tr": FAKE_RESULT.model_copy(deep=True),
    )


@pytest.fixture()
def completed_resume_id(client: TestClient, auth_headers, mock_llm) -> int:
    return upload_pdf(client, auth_headers).json()["id"]


class TestAtsEndpoint:
    def test_requires_auth(self, client: TestClient):
        assert client.post("/api/v1/resumes/1/ats-analysis", json={}).status_code == 401

    def test_resume_not_found(self, client: TestClient, auth_headers):
        resp = client.post("/api/v1/resumes/9999/ats-analysis", json={}, headers=auth_headers)
        assert resp.status_code == 404

    def test_conflict_when_not_parsed(
        self, client: TestClient, auth_headers, monkeypatch, mock_ats
    ):
        # Parse'ı başarısız kıl -> analiz 409 dönmeli
        def boom(text):
            raise RuntimeError("parse yok")

        import app.workers.tasks as tasks_module

        monkeypatch.setattr(tasks_module, "parse_resume_text", boom)
        resume_id = upload_pdf(client, auth_headers).json()["id"]

        resp = client.post(
            f"/api/v1/resumes/{resume_id}/ats-analysis", json={}, headers=auth_headers
        )
        assert resp.status_code == 409

    def test_unknown_job_posting_404(
        self, client: TestClient, auth_headers, completed_resume_id, mock_ats
    ):
        resp = client.post(
            f"/api/v1/resumes/{completed_resume_id}/ats-analysis",
            json={"job_posting_id": 4242},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_success_schema_and_persistence(
        self, client: TestClient, auth_headers, completed_resume_id, mock_ats
    ):
        resp = client.post(
            f"/api/v1/resumes/{completed_resume_id}/ats-analysis",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()

        # Şema alanları
        assert set(body["category_scores"].keys()) == set(CATEGORY_WEIGHTS.keys())
        assert body["strengths"] == FAKE_RESULT.strengths
        assert body["gaps"][0] == {
            "issue": FAKE_RESULT.gaps[0].issue,
            "why_it_matters": FAKE_RESULT.gaps[0].why_it_matters,
            "how_to_fix": FAKE_RESULT.gaps[0].how_to_fix,
        }
        # Toplam skor kategori toplamına eşit ve 100 sınırında
        assert body["total_score"] == sum(body["category_scores"].values()) == 76
        assert body["total_score"] <= 100
        # Disclaimer her çıktıda
        assert body["disclaimer"] == DISCLAIMER

    def test_llm_unavailable_returns_503(
        self, client: TestClient, auth_headers, completed_resume_id, monkeypatch
    ):
        from app.agents.ats_analyzer import AtsAnalysisError

        def boom(parsed, structure, job=None, language="tr"):
            raise AtsAnalysisError("ANTHROPIC_API_KEY tanımlı değil")

        monkeypatch.setattr("app.api.routes.resumes.analyze_resume", boom)
        resp = client.post(
            f"/api/v1/resumes/{completed_resume_id}/ats-analysis",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 503


class TestScoreReconciliation:
    def test_weights_sum_to_100(self):
        assert sum(CATEGORY_WEIGHTS.values()) == 100

    def test_clamp_fixes_overflow_and_total(self):
        # Model sınır aşarsa: kırpılmalı ve toplam yeniden hesaplanmalı
        result = AtsAnalysisResult.model_construct(
            total_score=999,
            category_scores=CategoryScores.model_construct(
                format_readability=99,   # max 15'e kırpılmalı
                contact_info=10,
                experience_quality=-5,   # 0'a kırpılmalı
                technical_skills=15,
                keyword_match=20,
                projects_achievements=15,
                language_quality=5,
            ),
            strengths=[],
            gaps=[],
        )
        fixed = _clamp_and_reconcile(result)
        assert fixed.category_scores.format_readability == 15
        assert fixed.category_scores.experience_quality == 0
        assert fixed.total_score == 15 + 10 + 0 + 15 + 20 + 15 + 5 == 80

    def test_perfect_scores_total_100(self):
        result = AtsAnalysisResult.model_construct(
            total_score=0,
            category_scores=CategoryScores(**{k: v for k, v in CATEGORY_WEIGHTS.items()}),
            strengths=[],
            gaps=[],
        )
        assert _clamp_and_reconcile(result).total_score == 100
