import pytest
from fastapi.testclient import TestClient

from app.agents.job_schema import ImprovementSuggestion, JobMatchResult, JobRequirements
from app.services.url_fetch import UrlFetchError, _TextExtractor, _validate_url
from tests.fixtures import register_and_login, upload_pdf

# Gerçekçi bir iş ilanı metni
JOB_TEXT = """\
Backend Developer (Python) — TechCo Yazılım A.Ş. / İstanbul (Hibrit)

TechCo olarak büyüyen ekibimize katılacak bir Backend Developer arıyoruz.

Aranan Nitelikler:
- Bilgisayar Mühendisliği veya ilgili bölümlerden mezun
- Python ile en az 3 yıl backend geliştirme deneyimi
- FastAPI veya Django ile RESTful API geliştirmiş olmak
- PostgreSQL ve ilişkisel veritabanı tasarımına hakimiyet
- Docker ile konteynerizasyon deneyimi
- Git ile versiyon kontrolü
- İyi derecede İngilizce (teknik dokümantasyon okuyabilecek seviyede)

Tercih Sebepleri:
- Kubernetes deneyimi
- AWS veya benzeri bulut platformlarında çalışmış olmak
- Celery ile asenkron görev yönetimi
- CI/CD süreçlerine hakimiyet

Sorumluluklar:
- Mikroservis mimarisinde yeni servisler geliştirmek
- Mevcut API'lerin performansını iyileştirmek
- Kod incelemelerine katılmak ve teknik dokümantasyon hazırlamak
"""

FAKE_REQUIREMENTS = JobRequirements(
    required_skills=[
        "Python", "FastAPI", "RESTful API", "PostgreSQL", "Docker", "Git", "İngilizce",
    ],
    preferred_skills=["Kubernetes", "AWS", "Celery", "CI/CD"],
    experience_years="en az 3 yıl",
    programming_languages=["Python"],
    tools_and_technologies=[
        "FastAPI", "Django", "PostgreSQL", "Docker", "Git", "Kubernetes", "AWS", "Celery",
    ],
    education_requirement="Bilgisayar Mühendisliği veya ilgili bölüm",
    language_requirement="İyi derecede İngilizce",
    key_responsibilities=[
        "Mikroservis mimarisinde yeni servisler geliştirmek",
        "Mevcut API'lerin performansını iyileştirmek",
        "Kod incelemelerine katılmak",
    ],
)

# Örnek CV (fixtures.FAKE_PARSED) ile bu ilanın gerçekçi eşleşmesi:
# CV'de var: Python, FastAPI, PostgreSQL, Docker, Git, İngilizce B2
# CV'de yok: Kubernetes, AWS (sertifika var ama deneyim yok), Celery, CI/CD
FAKE_MATCH = JobMatchResult(
    match_percentage=78,
    matched_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "İngilizce"],
    missing_skills=["Kubernetes", "AWS", "Celery", "CI/CD"],
    improvement_suggestions=[
        ImprovementSuggestion(
            suggestion=(
                "Mikroservislerinizi CI/CD hattıyla dağıttıysanız, deneyim maddenizde "
                "bunu açıkça belirtin."
            ),
            reason="İlan CI/CD süreçlerine hakimiyeti tercih sebebi olarak listeliyor.",
        ),
        ImprovementSuggestion(
            suggestion=(
                "Bu pozisyon için Kubernetes önemli görünüyor; öğrenmeniz eşleşme "
                "oranınızı artırabilir."
            ),
            reason="Kubernetes ilanda tercih edilen beceriler arasında yer alıyor.",
        ),
    ],
)


@pytest.fixture()
def mock_job_agent(monkeypatch):
    calls: dict[str, list] = {"extract": [], "match": []}

    def fake_extract(job_text: str, language="tr"):
        calls["extract"].append(job_text)
        return FAKE_REQUIREMENTS.model_copy(deep=True)

    def fake_match(resume_content, job_title, requirements, job_description, language="tr"):
        calls["match"].append(
            {
                "resume_content": resume_content,
                "job_title": job_title,
                "requirements": requirements,
            }
        )
        return FAKE_MATCH.model_copy(deep=True)

    monkeypatch.setattr("app.api.routes.job_postings.extract_requirements", fake_extract)
    monkeypatch.setattr("app.api.routes.job_postings.match_resume_to_job", fake_match)
    return calls


def create_posting(client: TestClient, headers, **overrides) -> dict:
    payload = {
        "raw_text": JOB_TEXT,
        "title": "Backend Developer (Python)",
        "company": "TechCo Yazılım A.Ş.",
        "location": "İstanbul",
        **overrides,
    }
    return client.post("/api/v1/job-postings", json=payload, headers=headers).json()


class TestCreateJobPosting:
    def test_requires_auth(self, client: TestClient):
        resp = client.post("/api/v1/job-postings", json={"raw_text": JOB_TEXT})
        assert resp.status_code == 401

    def test_requires_text_or_url(self, client: TestClient, auth_headers):
        resp = client.post("/api/v1/job-postings", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_rejects_too_short_text(self, client: TestClient, auth_headers, mock_job_agent):
        resp = client.post(
            "/api/v1/job-postings", json={"raw_text": "Backend arıyoruz"}, headers=auth_headers
        )
        assert resp.status_code == 400

    def test_extracts_requirements_from_pasted_text(
        self, client: TestClient, auth_headers, mock_job_agent
    ):
        resp = client.post(
            "/api/v1/job-postings",
            json={"raw_text": JOB_TEXT, "title": "Backend Developer (Python)"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        req = body["requirements"]
        assert "Python" in req["required_skills"]
        assert "Kubernetes" in req["preferred_skills"]
        assert req["experience_years"] == "en az 3 yıl"
        assert req["programming_languages"] == ["Python"]
        assert len(req["key_responsibilities"]) == 3
        assert JOB_TEXT.strip() in mock_job_agent["extract"][0]

    def test_url_fetch_error_returns_400(
        self, client: TestClient, auth_headers, monkeypatch, mock_job_agent
    ):
        def boom(url: str):
            raise UrlFetchError("Güvenlik nedeniyle yerel/özel ağ adreslerinden içerik çekilemez.")

        monkeypatch.setattr("app.api.routes.job_postings.fetch_job_text", boom)
        resp = client.post(
            "/api/v1/job-postings",
            json={"url": "http://169.254.169.254/latest/meta-data/"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "yerel/özel ağ" in resp.json()["detail"]

    def test_url_path_uses_fetched_text(
        self, client: TestClient, auth_headers, monkeypatch, mock_job_agent
    ):
        monkeypatch.setattr(
            "app.api.routes.job_postings.fetch_job_text", lambda url: JOB_TEXT
        )
        resp = client.post(
            "/api/v1/job-postings",
            json={"url": "https://example.com/jobs/backend", "title": "Backend Developer"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["url"] == "https://example.com/jobs/backend"
        assert mock_job_agent["extract"][0] == JOB_TEXT


class TestMatch:
    def test_requires_resume_reference(
        self, client: TestClient, auth_headers, mock_job_agent
    ):
        posting = create_posting(client, auth_headers)
        resp = client.post(
            f"/api/v1/job-postings/{posting['id']}/match", headers=auth_headers
        )
        assert resp.status_code == 400

    def test_unknown_version_404(self, client: TestClient, auth_headers, mock_job_agent):
        posting = create_posting(client, auth_headers)
        resp = client.post(
            f"/api/v1/job-postings/{posting['id']}/match?resume_version_id=999",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_match_against_parsed_resume(
        self, client: TestClient, auth_headers, mock_llm, mock_job_agent
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]
        posting = create_posting(client, auth_headers)

        resp = client.post(
            f"/api/v1/job-postings/{posting['id']}/match?resume_id={resume_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()

        assert body["match_percentage"] == 78
        assert 0 <= body["match_percentage"] <= 100
        assert "Python" in body["matched_skills"]
        assert "Kubernetes" in body["missing_skills"]
        assert set(body["matched_skills"]).isdisjoint(body["missing_skills"])
        assert body["improvement_suggestions"][0]["suggestion"]
        assert body["improvement_suggestions"][0]["reason"]
        # Ajan CV içeriğini ve ilanın çıkarılmış gereksinimlerini almalı
        call = mock_job_agent["match"][0]
        assert call["resume_content"]["skills"] == [
            "Python", "FastAPI", "PostgreSQL", "Docker", "Git",
        ]
        assert "Python" in call["requirements"]["required_skills"]

    def test_match_against_resume_version(
        self, client: TestClient, auth_headers, mock_llm, mock_job_agent, monkeypatch
    ):
        from tests.test_rewrite import FAKE_REWRITE

        monkeypatch.setattr(
            "app.api.routes.resumes.rewrite_resume",
            lambda *a, **kw: FAKE_REWRITE.model_copy(deep=True),
        )
        resume_id = upload_pdf(client, auth_headers).json()["id"]
        version = client.post(
            f"/api/v1/resumes/{resume_id}/rewrite",
            json={"edit_level": "light"},
            headers=auth_headers,
        ).json()
        posting = create_posting(client, auth_headers)

        resp = client.post(
            f"/api/v1/job-postings/{posting['id']}/match?resume_version_id={version['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["resume_version_id"] == version["id"]
        # Eşleştirme versiyonun içeriğiyle yapılmalı, parsed_json ile değil
        assert (
            mock_job_agent["match"][0]["resume_content"]["experience"][0]["description"]
            == FAKE_REWRITE.updated_content.experience[0].description
        )

    def test_rerun_updates_existing_match(
        self, client: TestClient, auth_headers, mock_llm, mock_job_agent
    ):
        resume_id = upload_pdf(client, auth_headers).json()["id"]
        posting = create_posting(client, auth_headers)
        url = f"/api/v1/job-postings/{posting['id']}/match?resume_id={resume_id}"

        first = client.post(url, headers=auth_headers).json()
        second = client.post(url, headers=auth_headers).json()

        assert first["id"] == second["id"]  # yeni kayıt değil, güncelleme
        matches = client.get(
            f"/api/v1/job-postings/{posting['id']}/matches", headers=auth_headers
        ).json()
        assert len(matches) == 1

    def test_other_user_cannot_match(
        self, client: TestClient, auth_headers, mock_llm, mock_job_agent
    ):
        posting = create_posting(client, auth_headers)
        other = {"email": "other@example.com", "password": "sifre1234"}
        token = register_and_login(client, other)

        resp = client.post(
            f"/api/v1/job-postings/{posting['id']}/match?resume_id=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestUrlSafety:
    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost:8000/admin",
            "http://127.0.0.1/",
            "http://169.254.169.254/latest/meta-data/",  # cloud metadata
            "http://[::1]/",
        ],
    )
    def test_blocks_private_and_loopback(self, url):
        with pytest.raises(UrlFetchError):
            _validate_url(url)

    @pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "gopher://x"])
    def test_blocks_non_http_schemes(self, url):
        with pytest.raises(UrlFetchError):
            _validate_url(url)

    def test_allowlist_blocks_other_domains(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.config.settings.ALLOWED_JOB_DOMAINS", "kariyer.net,linkedin.com"
        )
        with pytest.raises(UrlFetchError, match="izin verilmiyor"):
            _validate_url("https://example.com/jobs/1")

    def test_html_text_extraction_drops_scripts(self):
        parser = _TextExtractor()
        parser.feed(
            "<html><head><style>.x{color:red}</style></head><body>"
            "<script>alert('x')</script><h1>Backend Developer</h1>"
            "<p>Python ile 3 yıl deneyim</p></body></html>"
        )
        text = parser.get_text()
        assert "Backend Developer" in text
        assert "Python ile 3 yıl deneyim" in text
        assert "alert" not in text
        assert "color:red" not in text
