import re

import pytest
from fastapi.testclient import TestClient

from app.agents.linkedin_optimizer import _truncate_headline
from app.agents.linkedin_schema import (
    CHECKLIST_ITEMS,
    HEADLINE_MAX_LENGTH,
    ChecklistItem,
    ExperienceDescription,
    LinkedInOptimization,
)
from tests.fixtures import upload_pdf
from tests.test_job_match import mock_job_agent  # noqa: F401  (fixture olarak kullanılıyor)

ABOUT = """\
Backend tarafında Python ve FastAPI ile çalışıyorum. Acme Yazılım'da mikroservisler geliştiriyor, servisler arası iletişimin ve veri katmanının sağlıklı işlemesinden sorumlu oluyorum.

Günlük işimin önemli bir kısmı PostgreSQL tarafında geçiyor: sorgu planlarını inceleyip yavaş çalışan sorguları elden geçiriyorum. Servisleri Docker ile paketleyip çalıştırıyorum.

İstanbul Teknik Üniversitesi Bilgisayar Mühendisliği mezunuyum. Boş zamanlarımda CV Agent adında bir yan proje geliştiriyorum; Claude API'yi kullanarak CV'lerden yapılandırılmış veri çıkaran bir kariyer asistanı.

Şu sıralar backend tarafında daha derinleşmek istediğim alan dağıtık sistemler. Yeni bir pozisyonda bu yönde çalışabileceğim bir ekipte yer almak isterim."""

FAKE_RESULT = LinkedInOptimization(
    headline_options=[
        "Backend Developer | Python, FastAPI, PostgreSQL | Mikroservis geliştirme",
        "Python Backend Developer @ Acme Yazılım — API tasarımı ve veritabanı optimizasyonu",
        "Backend Developer | FastAPI ile REST API geliştiriyor, PostgreSQL sorgularını optimize ediyorum",
    ],
    about_section=ABOUT,
    experience_descriptions=[
        ExperienceDescription(
            role="Backend Developer",
            linkedin_version=(
                "Acme Yazılım'da Python ve FastAPI ile mikroservisler geliştiriyorum. "
                "PostgreSQL tarafında sorgu optimizasyonu üzerine çalışıyor, servisleri "
                "Docker ile paketliyorum."
            ),
        )
    ],
    # CV'de geçen: Python, FastAPI, PostgreSQL, Docker, Git
    # Yakın çıkarım: REST APIs (FastAPI), SQL (PostgreSQL), Microservices (deneyimde geçiyor)
    suggested_skills=[
        "Python",
        "FastAPI",
        "PostgreSQL",
        "Docker",
        "Git",
        "REST APIs",
        "SQL",
        "Microservices",
    ],
    profile_completeness_checklist=[
        ChecklistItem(item="Profil fotoğrafı", present=None),
        ChecklistItem(item="Arka plan (banner) görseli", present=None),
        ChecklistItem(item="Başlık (headline)", present=True),
        ChecklistItem(item="Hakkında (about) bölümü", present=False),
        ChecklistItem(item="Güncel pozisyon ve açıklaması", present=True),
        ChecklistItem(item="Eğitim bilgisi", present=True),
        ChecklistItem(item="Beceriler (en az 5 adet)", present=True),
        ChecklistItem(item="Sertifikalar", present=True),
        ChecklistItem(item="Diller", present=False),
        ChecklistItem(item="Öne çıkan projeler", present=False),
        ChecklistItem(item="Özel profil URL'si", present=None),
        ChecklistItem(item="İletişim bilgileri", present=True),
    ],
)


@pytest.fixture()
def mock_linkedin(monkeypatch):
    calls: list[dict] = []

    def fake(resume_content, target_role=None, job_requirements=None, language="tr"):
        calls.append(
            {
                "resume_content": resume_content,
                "target_role": target_role,
                "job_requirements": job_requirements,
            }
        )
        return FAKE_RESULT.model_copy(deep=True)

    monkeypatch.setattr("app.api.routes.linkedin.optimize_profile", fake)
    return calls


@pytest.fixture()
def resume_id(client: TestClient, auth_headers, mock_llm) -> int:
    return upload_pdf(client, auth_headers).json()["id"]


@pytest.fixture()
def result(client: TestClient, auth_headers, resume_id, mock_linkedin) -> dict:
    resp = client.post(
        f"/api/v1/linkedin/optimize?resume_id={resume_id}", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestEndpoint:
    def test_requires_auth(self, client: TestClient):
        assert client.post("/api/v1/linkedin/optimize?resume_id=1").status_code == 401

    def test_requires_resume_reference(self, client: TestClient, auth_headers, mock_linkedin):
        resp = client.post("/api/v1/linkedin/optimize", headers=auth_headers)
        assert resp.status_code == 400

    def test_unknown_version_404(self, client: TestClient, auth_headers, mock_linkedin):
        resp = client.post(
            "/api/v1/linkedin/optimize?resume_version_id=999", headers=auth_headers
        )
        assert resp.status_code == 404

    def test_uses_resume_version_content(
        self, client: TestClient, auth_headers, resume_id, mock_linkedin, monkeypatch
    ):
        from tests.test_rewrite import FAKE_REWRITE

        monkeypatch.setattr(
            "app.api.routes.resumes.rewrite_resume",
            lambda *a, **kw: FAKE_REWRITE.model_copy(deep=True),
        )
        version = client.post(
            f"/api/v1/resumes/{resume_id}/rewrite",
            json={"edit_level": "light"},
            headers=auth_headers,
        ).json()

        resp = client.post(
            f"/api/v1/linkedin/optimize?resume_version_id={version['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert (
            mock_linkedin[0]["resume_content"]["experience"][0]["description"]
            == FAKE_REWRITE.updated_content.experience[0].description
        )

    def test_passes_target_role_and_job_requirements(
        self, client: TestClient, auth_headers, resume_id, mock_linkedin, mock_job_agent
    ):
        from tests.test_job_match import create_posting

        posting = create_posting(client, auth_headers)
        resp = client.post(
            f"/api/v1/linkedin/optimize?resume_id={resume_id}"
            f"&target_role=Senior Backend Developer&job_posting_id={posting['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert mock_linkedin[0]["target_role"] == "Senior Backend Developer"
        assert "Python" in mock_linkedin[0]["job_requirements"]["required_skills"]

    def test_llm_unavailable_returns_503(
        self, client: TestClient, auth_headers, resume_id, monkeypatch
    ):
        from app.agents.linkedin_optimizer import LinkedInAgentError

        def boom(*args, **kwargs):
            raise LinkedInAgentError("ANTHROPIC_API_KEY tanımlı değil")

        monkeypatch.setattr("app.api.routes.linkedin.optimize_profile", boom)
        resp = client.post(
            f"/api/v1/linkedin/optimize?resume_id={resume_id}", headers=auth_headers
        )
        assert resp.status_code == 503


class TestHeadlineLimit:
    """LinkedIn'in 220 karakter sınırının aşılmadığını doğrular."""

    def test_three_options_returned(self, result):
        assert len(result["headline_options"]) == 3

    def test_no_option_exceeds_limit(self, result):
        for headline in result["headline_options"]:
            assert len(headline) <= HEADLINE_MAX_LENGTH, (
                f"{len(headline)} karakter, sınır {HEADLINE_MAX_LENGTH}: {headline}"
            )

    def test_limit_exposed_to_client(self, result):
        assert result["headline_max_length"] == HEADLINE_MAX_LENGTH

    def test_headlines_are_not_empty(self, result):
        assert all(h.strip() for h in result["headline_options"])

    def test_options_are_distinct(self, result):
        assert len(set(result["headline_options"])) == 3

    # --- Sunucu tarafı güvence: model sınırı ihlal ederse ---

    def test_truncate_keeps_short_headline_untouched(self):
        short = "Backend Developer | Python, FastAPI"
        assert _truncate_headline(short) == short

    def test_truncate_clamps_overlong_headline(self):
        overlong = "Backend Developer " * 20  # ~360 karakter
        assert len(overlong) > HEADLINE_MAX_LENGTH
        clamped = _truncate_headline(overlong)
        assert len(clamped) <= HEADLINE_MAX_LENGTH
        assert clamped.endswith("…")

    def test_truncate_breaks_on_word_boundary(self):
        overlong = "Python FastAPI PostgreSQL Docker Kubernetes " * 8
        clamped = _truncate_headline(overlong)
        source_words = overlong.split()
        # Kırpılan metnin her kelimesi kaynakta tam olarak bulunmalı
        # (kelime ortasından kesilmiş bir parça kalmamalı)
        for word in clamped.rstrip("…").split():
            assert word in source_words, f"Kelime ortasından kesilmiş: {word}"

    def test_exactly_at_limit_is_kept(self):
        exact = "A" * HEADLINE_MAX_LENGTH
        assert _truncate_headline(exact) == exact
        assert len(_truncate_headline(exact)) == HEADLINE_MAX_LENGTH

    def test_agent_clamps_before_returning(self, monkeypatch):
        """Model 220'yi aşan başlık dönerse agent kırpmalı."""
        import app.agents.linkedin_optimizer as module

        overlong = LinkedInOptimization(
            **{
                **FAKE_RESULT.model_dump(),
                "headline_options": ["X" * 400, "Kısa başlık", "Y" * 250],
            }
        )

        monkeypatch.setattr(module.llm, "parse_structured", lambda *a, **kw: overlong)

        result = module.optimize_profile({"skills": []})
        assert all(len(h) <= HEADLINE_MAX_LENGTH for h in result.headline_options)
        assert result.headline_options[1] == "Kısa başlık"  # kısa olan bozulmamalı


class TestAboutSection:
    def test_paragraph_count_in_range(self, result):
        paragraphs = [p for p in result["about_section"].split("\n\n") if p.strip()]
        assert 3 <= len(paragraphs) <= 5, f"{len(paragraphs)} paragraf"

    def test_avoids_cliches(self, result):
        cliches = [
            "çalışkanım",
            "disiplinliyim",
            "takım oyuncusuyum",
            "detay odaklıyım",
            "hızlı öğrenirim",
            "kendimi geliştirmeye açığım",
        ]
        about = result["about_section"].lower()
        for cliche in cliches:
            assert cliche not in about, f"Klişe ifade bulundu: {cliche}"

    def test_is_substantive(self, result):
        assert len(result["about_section"]) > 300


class TestSuggestedSkills:
    def test_no_fabricated_skills(self, result):
        """CV'de hiçbir container/orkestrasyon izi yoksa Kubernetes önerilmemeli."""
        assert "Kubernetes" not in result["suggested_skills"]
        for fabricated in ("AWS", "Terraform", "Machine Learning", "Kafka"):
            assert fabricated not in result["suggested_skills"]

    def test_includes_cv_skills(self, result):
        for skill in ("Python", "FastAPI", "PostgreSQL", "Docker", "Git"):
            assert skill in result["suggested_skills"]

    def test_adjacent_inferences_allowed(self, result):
        # FastAPI -> REST APIs makul yakın çıkarım
        assert "REST APIs" in result["suggested_skills"]

    def test_every_skill_is_grounded(self, result, mock_linkedin):
        """Her önerilen beceri ya CV'de geçmeli ya da bilinen yakın çıkarım olmalı."""
        cv_text = str(mock_linkedin[0]["resume_content"]).lower()
        adjacency = {
            "rest apis": "fastapi",
            "sql": "postgresql",
            "microservices": "mikroservis",
        }
        for skill in result["suggested_skills"]:
            key = skill.lower()
            grounded = key in cv_text or adjacency.get(key, "\0") in cv_text
            assert grounded, f"Dayanaksız beceri önerisi: {skill}"


class TestChecklist:
    def test_covers_standard_items(self, result):
        items = [entry["item"] for entry in result["profile_completeness_checklist"]]
        assert items == CHECKLIST_ITEMS

    def test_present_is_tri_state(self, result):
        values = {entry["present"] for entry in result["profile_completeness_checklist"]}
        assert values <= {True, False, None}
        assert None in values  # CV'den anlaşılamayan maddeler null olmalı

    def test_unknowable_items_are_null(self, result):
        by_item = {
            entry["item"]: entry["present"]
            for entry in result["profile_completeness_checklist"]
        }
        assert by_item["Profil fotoğrafı"] is None
        assert by_item["Özel profil URL'si"] is None
        assert by_item["Eğitim bilgisi"] is True
