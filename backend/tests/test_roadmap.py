import re

import pytest
from fastapi.testclient import TestClient

from app.agents.career_coach import CareerRoadmapResult, DevelopmentStep
from tests.fixtures import register_and_login, upload_pdf
from tests.test_job_match import create_posting
from tests.test_job_match import mock_job_agent  # noqa: F401  (fixture olarak kullanılıyor)

TARGET_ROLE = "Senior Backend Developer"

FAKE_ROADMAP = CareerRoadmapResult(
    current_strengths=[
        "Python ve FastAPI ile üretim ortamında mikroservis geliştirme deneyimi (Acme Yazılım)",
        "PostgreSQL sorgu optimizasyonu üzerinde somut çalışma",
        "Docker ile konteynerizasyon pratiği",
    ],
    gaps=[
        "Kubernetes ile orkestrasyon deneyimi görünmüyor",
        "Asenkron görev yönetimi (Celery vb.) CV'de yer almıyor",
        "Otomatik test kapsamına dair bir kanıt yok",
    ],
    development_plan=[
        DevelopmentStep(
            step=1,
            action=(
                "Mevcut CV Agent projenize pytest ile en az %70 satır kapsamı sağlayan "
                "bir test suite ekleyin ve kapsam raporunu README'ye koyun."
            ),
            estimated_effort="1-2 hafta, haftada ~5 saat",
        ),
        DevelopmentStep(
            step=2,
            action=(
                "FastAPI servisinize Celery + Redis ile asenkron bir görev kuyruğu ekleyin "
                "ve uzun süren bir işlemi (ör. rapor üretimi) arka plana taşıyın."
            ),
            estimated_effort="2-3 hafta, haftada ~6 saat",
        ),
        DevelopmentStep(
            step=3,
            action=(
                "Projenizi GitHub Actions ile test + lint çalıştıran bir CI hattına bağlayın "
                "ve her PR'da yeşil build zorunluluğu tanımlayın."
            ),
            estimated_effort="3-5 gün, günde ~2 saat",
        ),
        DevelopmentStep(
            step=4,
            action=(
                "Uygulamanızı minikube üzerinde Deployment ve Service manifestleriyle "
                "çalıştırın; manifestleri repoda k8s/ klasöründe versiyonlayın."
            ),
            estimated_effort="1-2 ay düzenli pratik",
        ),
    ],
)


@pytest.fixture()
def mock_coach(monkeypatch):
    calls: list[dict] = []

    def fake(resume_content, target_role, job_requirements=None, job_description=None, profile_goal=None, language="tr"):
        calls.append(
            {
                "resume_content": resume_content,
                "target_role": target_role,
                "job_requirements": job_requirements,
                "profile_goal": profile_goal,
            }
        )
        return FAKE_ROADMAP.model_copy(deep=True)

    monkeypatch.setattr("app.api.routes.roadmap.build_roadmap", fake)
    return calls


@pytest.fixture()
def resume_id(client: TestClient, auth_headers, mock_llm) -> int:
    return upload_pdf(client, auth_headers).json()["id"]


class TestRoadmapEndpoint:
    def test_requires_auth(self, client: TestClient):
        resp = client.get("/api/v1/career-roadmap?target_role=X&resume_id=1")
        assert resp.status_code == 401

    def test_requires_target_role(self, client: TestClient, auth_headers, resume_id):
        resp = client.get(
            f"/api/v1/career-roadmap?resume_id={resume_id}", headers=auth_headers
        )
        assert resp.status_code == 422

    def test_requires_resume_reference(self, client: TestClient, auth_headers, mock_coach):
        resp = client.get(
            f"/api/v1/career-roadmap?target_role={TARGET_ROLE}", headers=auth_headers
        )
        assert resp.status_code == 400

    def test_unknown_version_404(self, client: TestClient, auth_headers, mock_coach):
        resp = client.get(
            f"/api/v1/career-roadmap?target_role={TARGET_ROLE}&resume_version_id=999",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_generates_roadmap_without_job_posting(
        self, client: TestClient, auth_headers, resume_id, mock_coach
    ):
        resp = client.get(
            f"/api/v1/career-roadmap?target_role={TARGET_ROLE}&resume_id={resume_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["target_role"] == TARGET_ROLE
        assert len(body["current_strengths"]) == 3
        assert len(body["gaps"]) == 3
        assert body["completed_steps"] == []
        assert body["progress_percentage"] == 0
        # İlan yoksa ajana gereksinim gönderilmemeli
        assert mock_coach[0]["job_requirements"] is None
        assert mock_coach[0]["resume_content"]["skills"][0] == "Python"

    def test_uses_job_posting_when_provided(
        self, client: TestClient, auth_headers, resume_id, mock_coach, mock_job_agent
    ):
        posting = create_posting(client, auth_headers)
        resp = client.get(
            f"/api/v1/career-roadmap?target_role={TARGET_ROLE}"
            f"&resume_id={resume_id}&job_posting_id={posting['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["job_posting_id"] == posting["id"]
        assert "Python" in mock_coach[0]["job_requirements"]["required_skills"]

    def test_unknown_job_posting_404(
        self, client: TestClient, auth_headers, resume_id, mock_coach
    ):
        resp = client.get(
            f"/api/v1/career-roadmap?target_role={TARGET_ROLE}"
            f"&resume_id={resume_id}&job_posting_id=999",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_is_idempotent_and_refresh_regenerates(
        self, client: TestClient, auth_headers, resume_id, mock_coach
    ):
        url = f"/api/v1/career-roadmap?target_role={TARGET_ROLE}&resume_id={resume_id}"
        first = client.get(url, headers=auth_headers).json()
        second = client.get(url, headers=auth_headers).json()

        assert first["id"] == second["id"]
        assert len(mock_coach) == 1  # ikinci GET modeli tekrar çağırmamalı

        client.get(f"{url}&refresh=true", headers=auth_headers)
        assert len(mock_coach) == 2

    def test_llm_unavailable_returns_503(
        self, client: TestClient, auth_headers, resume_id, monkeypatch
    ):
        from app.agents.career_coach import CareerCoachError

        def boom(*args, **kwargs):
            raise CareerCoachError("ANTHROPIC_API_KEY tanımlı değil")

        monkeypatch.setattr("app.api.routes.roadmap.build_roadmap", boom)
        resp = client.get(
            f"/api/v1/career-roadmap?target_role={TARGET_ROLE}&resume_id={resume_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 503


class TestDevelopmentPlanQuality:
    """development_plan adımlarının somut ve uygulanabilir olduğunu doğrular."""

    VAGUE_PATTERNS = [
        r"daha iyi ol",
        r"kendinizi geliştir",
        r"networking yap",
        r"çok çalış",
        r"araştır(ın)?$",
        r"öğrenin$",
    ]

    @pytest.fixture()
    def plan(self, client: TestClient, auth_headers, resume_id, mock_coach) -> list[dict]:
        return client.get(
            f"/api/v1/career-roadmap?target_role={TARGET_ROLE}&resume_id={resume_id}",
            headers=auth_headers,
        ).json()["development_plan"]

    def test_steps_are_sequential(self, plan):
        assert [s["step"] for s in plan] == list(range(1, len(plan) + 1))

    def test_plan_size_is_actionable(self, plan):
        assert 4 <= len(plan) <= 7

    def test_actions_are_not_vague(self, plan):
        for step in plan:
            action = step["action"].lower()
            for pattern in self.VAGUE_PATTERNS:
                assert not re.search(pattern, action), f"Muğlak ifade: {step['action']}"

    def test_actions_are_specific_enough(self, plan):
        for step in plan:
            # Somut bir adım: yeterince uzun ve bir eylem fiili içeriyor
            assert len(step["action"]) > 40, f"Çok kısa/genel adım: {step['action']}"
            assert re.search(
                r"(ekleyin|yazın|kurun|bağlayın|çalıştırın|oluşturun|taşıyın|"
                r"versiyonlayın|tanımlayın|koyun|uygulayın|yayınlayın)",
                step["action"].lower(),
            ), f"Eylem fiili yok: {step['action']}"

    def test_effort_estimates_are_ranges_not_promises(self, plan):
        for step in plan:
            effort = step["estimated_effort"].lower()
            assert re.search(r"(gün|hafta|ay)", effort), f"Süre birimi yok: {effort}"
            # Gerçekçilik: aralık veya yaklaşık ifade içermeli
            assert ("-" in effort) or ("~" in effort) or ("düzenli" in effort), (
                f"Kesin tek süre verilmiş: {effort}"
            )


class TestProgressTracking:
    @pytest.fixture()
    def roadmap(self, client: TestClient, auth_headers, resume_id, mock_coach) -> dict:
        return client.get(
            f"/api/v1/career-roadmap?target_role={TARGET_ROLE}&resume_id={resume_id}",
            headers=auth_headers,
        ).json()

    def test_mark_steps_completed(self, client: TestClient, auth_headers, roadmap):
        resp = client.patch(
            f"/api/v1/career-roadmap/{roadmap['id']}/progress",
            json={"completed_steps": [1, 2]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["completed_steps"] == [1, 2]
        assert body["progress_percentage"] == 50  # 4 adımın 2'si

    def test_progress_persists_across_get(
        self, client: TestClient, auth_headers, resume_id, roadmap
    ):
        client.patch(
            f"/api/v1/career-roadmap/{roadmap['id']}/progress",
            json={"completed_steps": [1]},
            headers=auth_headers,
        )
        again = client.get(
            f"/api/v1/career-roadmap?target_role={TARGET_ROLE}&resume_id={resume_id}",
            headers=auth_headers,
        ).json()
        assert again["completed_steps"] == [1]
        assert again["progress_percentage"] == 25

    def test_unchecking_works(self, client: TestClient, auth_headers, roadmap):
        url = f"/api/v1/career-roadmap/{roadmap['id']}/progress"
        client.patch(url, json={"completed_steps": [1, 2, 3]}, headers=auth_headers)
        resp = client.patch(url, json={"completed_steps": [1]}, headers=auth_headers)
        assert resp.json()["completed_steps"] == [1]

    def test_invalid_step_rejected(self, client: TestClient, auth_headers, roadmap):
        resp = client.patch(
            f"/api/v1/career-roadmap/{roadmap['id']}/progress",
            json={"completed_steps": [99]},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_other_user_cannot_update(self, client: TestClient, auth_headers, roadmap):
        other = {"email": "other@example.com", "password": "sifre1234"}
        token = register_and_login(client, other)
        resp = client.patch(
            f"/api/v1/career-roadmap/{roadmap['id']}/progress",
            json={"completed_steps": [1]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
