import pytest
from fastapi.testclient import TestClient

from app.agents.interview_agent import has_cv_grounded_question
from app.agents.interview_schema import (
    POOL_SAMPLE_SIZE,
    QUESTION_POOL,
    InterviewQuestion,
    InterviewQuestionSet,
    QuestionSource,
    SessionType,
)
from tests.fixtures import FAKE_PARSED, register_and_login, upload_pdf
from tests.test_job_match import create_posting
from tests.test_job_match import mock_job_agent  # noqa: F401  (fixture olarak kullanılıyor)

CV_CONTENT = FAKE_PARSED.model_dump()


def q(question: str, category: str, source: QuestionSource, star: bool) -> InterviewQuestion:
    return InterviewQuestion(
        question=question, category=category, source=source, star_applicable=star
    )


# Davranışsal görüşme için gerçekçi çıktı: 5 genel (havuzdan çeşitlendirilmiş),
# 3 CV'ye özel (CV'deki gerçek şirket/proje/teknolojiye atıfla), 2 ilana özel.
FAKE_BEHAVIORAL = InterviewQuestionSet(
    questions=[
        q("Bir ekip arkadaşınızla fikir ayrılığı yaşadığınız bir durumu anlatır mısınız?",
          "Çatışma yönetimi", QuestionSource.GENERAL, True),
        q("Beklediğiniz gibi gitmeyen bir projeyi ve oradan ne öğrendiğinizi anlatın.",
          "Başarısızlıktan öğrenme", QuestionSource.GENERAL, True),
        q("Teslim tarihi baskısı altında çalıştığınız bir örneği paylaşır mısınız?",
          "Baskı altında çalışma", QuestionSource.GENERAL, True),
        q("Kimse söylemeden bir sorunu üstlenip çözdüğünüz bir durumu anlatın.",
          "İnisiyatif", QuestionSource.GENERAL, True),
        q("Olumsuz bir geri bildirim aldığınız ve buna nasıl karşılık verdiğinizi anlatın.",
          "Geri bildirim", QuestionSource.GENERAL, True),
        q("Acme Yazılım'da mikroservis mimarisine geçerken karşılaştığınız en zor teknik "
          "kararı ve nasıl verdiğinizi anlatır mısınız?",
          "Acme Yazılım deneyimi", QuestionSource.CV_SPECIFIC, True),
        q("PostgreSQL sorgu optimizasyonu yaptığınız bir durumu anlatın: sorunu nasıl "
          "fark ettiniz ve sonuç ne oldu?",
          "PostgreSQL", QuestionSource.CV_SPECIFIC, True),
        q("FastAPI ile geliştirdiğiniz servislerde bir tasarım kararınızı ekibe "
          "savunmak zorunda kaldığınız bir örneği paylaşın.",
          "FastAPI", QuestionSource.CV_SPECIFIC, True),
        q("Docker ile konteynerize edilmiş bir serviste yaşadığınız bir üretim sorununu "
          "anlatır mısınız?", "Docker", QuestionSource.JOB_SPECIFIC, True),
        q("İlanda geçen RESTful API tasarımı konusunda bir tercihinizi gerekçelendirmek "
          "zorunda kaldığınız bir durumu anlatın.", "RESTful API",
          QuestionSource.JOB_SPECIFIC, True),
    ]
)

FAKE_TECHNICAL = InterviewQuestionSet(
    questions=[
        q("Üzerinde çalıştığınız bir sistemin mimarisini anlatır mısınız?",
          "Sistem tasarımı", QuestionSource.GENERAL, False),
        q("Karmaşık bir hatayı teşhis etme süreciniz nasıl işliyor?",
          "Hata ayıklama", QuestionSource.GENERAL, False),
        q("Kod kalitesini nasıl ölçüyor ve koruyorsunuz?", "Kod kalitesi",
          QuestionSource.GENERAL, False),
        q("Test stratejinizi nasıl kurguluyorsunuz?", "Test", QuestionSource.GENERAL, False),
        q("Bir performans darboğazını nasıl tespit edip giderirsiniz?", "Performans",
          QuestionSource.GENERAL, False),
        q("CV Agent projenizde Claude API'den gelen yapılandırılmış çıktıyı nasıl "
          "doğruluyorsunuz?", "CV Agent projesi", QuestionSource.CV_SPECIFIC, False),
        q("FastAPI'de bağımlılık enjeksiyonunu (Depends) hangi durumlarda "
          "kullanıyorsunuz?", "FastAPI", QuestionSource.CV_SPECIFIC, False),
        q("PostgreSQL'de bir sorgunun yavaş çalıştığını nasıl anlarsınız?", "PostgreSQL",
          QuestionSource.CV_SPECIFIC, False),
    ]
)


@pytest.fixture()
def mock_interview(monkeypatch):
    calls: list[dict] = []

    def fake(session_type, resume_content, job_title=None, job_requirements=None, language="tr"):
        calls.append(
            {
                "session_type": session_type,
                "resume_content": resume_content,
                "job_title": job_title,
                "job_requirements": job_requirements,
            }
        )
        result = (
            FAKE_TECHNICAL if session_type == SessionType.TECHNICAL else FAKE_BEHAVIORAL
        )
        return result.model_copy(deep=True)

    monkeypatch.setattr("app.api.routes.interview.generate_questions", fake)
    return calls


@pytest.fixture()
def resume_id(client: TestClient, auth_headers, mock_llm) -> int:
    return upload_pdf(client, auth_headers).json()["id"]


@pytest.fixture()
def session(client: TestClient, auth_headers, resume_id, mock_interview) -> dict:
    resp = client.post(
        "/api/v1/interview/questions",
        json={"session_type": "behavioral", "resume_id": resume_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestEndpoint:
    def test_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/v1/interview/questions",
            json={"session_type": "hr", "resume_id": 1},
        )
        assert resp.status_code == 401

    def test_invalid_session_type(self, client: TestClient, auth_headers, resume_id):
        resp = client.post(
            "/api/v1/interview/questions",
            json={"session_type": "smalltalk", "resume_id": resume_id},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_requires_resume_reference(self, client: TestClient, auth_headers, mock_interview):
        resp = client.post(
            "/api/v1/interview/questions",
            json={"session_type": "hr"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_unknown_version_404(self, client: TestClient, auth_headers, mock_interview):
        resp = client.post(
            "/api/v1/interview/questions",
            json={"session_type": "hr", "resume_version_id": 999},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_unknown_job_posting_404(
        self, client: TestClient, auth_headers, resume_id, mock_interview
    ):
        resp = client.post(
            "/api/v1/interview/questions",
            json={"session_type": "hr", "resume_id": resume_id, "job_posting_id": 999},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_llm_unavailable_returns_503(
        self, client: TestClient, auth_headers, resume_id, monkeypatch
    ):
        from app.agents.interview_agent import InterviewAgentError

        def boom(*args, **kwargs):
            raise InterviewAgentError("ANTHROPIC_API_KEY tanımlı değil")

        monkeypatch.setattr("app.api.routes.interview.generate_questions", boom)
        resp = client.post(
            "/api/v1/interview/questions",
            json={"session_type": "hr", "resume_id": resume_id},
            headers=auth_headers,
        )
        assert resp.status_code == 503


class TestOutputSchema:
    def test_question_fields(self, session):
        for question in session["questions"]:
            assert question["question"].strip()
            assert question["category"]
            assert question["source"] in ("general", "cv_specific", "job_specific")
            assert isinstance(question["star_applicable"], bool)

    def test_questions_are_ordered(self, session):
        indices = [q["order_index"] for q in session["questions"]]
        assert indices == sorted(indices) == list(range(len(indices)))

    def test_session_metadata_saved(self, session, resume_id):
        assert session["session_type"] == "behavioral"
        assert session["status"] == "prepared"
        assert session["resume_id"] == resume_id


class TestThreeSources:
    def test_general_questions_present(self, session):
        general = [q for q in session["questions"] if q["source"] == "general"]
        assert len(general) == POOL_SAMPLE_SIZE

    def test_cv_specific_questions_present(self, session):
        cv = [q for q in session["questions"] if q["source"] == "cv_specific"]
        assert len(cv) >= 3

    def test_cv_specific_references_real_cv_content(self, session):
        """CV'de geçen spesifik bir teknoloji/projeye referans veren soru olmalı."""
        cv_questions = [
            q["question"] for q in session["questions"] if q["source"] == "cv_specific"
        ]
        cv_terms = ["FastAPI", "PostgreSQL", "Acme Yazılım", "Docker", "CV Agent", "Python"]
        matching = [
            question
            for question in cv_questions
            if any(term.lower() in question.lower() for term in cv_terms)
        ]
        assert matching, f"CV'ye özel soruların hiçbiri CV içeriğine atıf yapmıyor: {cv_questions}"

    def test_job_specific_only_with_posting(
        self, client: TestClient, auth_headers, resume_id, mock_interview, mock_job_agent
    ):
        # İlansız: job_specific soru üretilmemeli (agent zaten filtreliyor)
        without = client.post(
            "/api/v1/interview/questions",
            json={"session_type": "technical", "resume_id": resume_id},
            headers=auth_headers,
        ).json()
        assert all(q["source"] != "job_specific" for q in without["questions"])

        # İlanlı: ilan bilgisi ajana geçmeli
        posting = create_posting(client, auth_headers)
        with_job = client.post(
            "/api/v1/interview/questions",
            json={
                "session_type": "behavioral",
                "resume_id": resume_id,
                "job_posting_id": posting["id"],
            },
            headers=auth_headers,
        ).json()
        assert with_job["job_posting_id"] == posting["id"]
        assert mock_interview[-1]["job_title"] == "Backend Developer (Python)"
        assert any(q["source"] == "job_specific" for q in with_job["questions"])


class TestStarFormat:
    def test_behavioral_questions_are_star_applicable(self, session):
        behavioral = [q for q in session["questions"] if q["source"] != "job_specific"]
        assert all(q["star_applicable"] for q in behavioral)

    def test_behavioral_questions_ask_for_past_experience(self, session):
        """STAR uyumu için sorular geçmiş somut bir olayı anlatmaya davet etmeli."""
        past_markers = ("anlatın", "anlatır mısınız", "paylaşın", "paylaşır mısınız")
        for question in session["questions"]:
            if not question["star_applicable"]:
                continue
            text = question["question"].lower()
            assert any(m in text for m in past_markers), f"STAR'a uygun değil: {text}"

    def test_behavioral_avoids_hypothetical_framing(self, session):
        for question in session["questions"]:
            assert "ne yapardınız" not in question["question"].lower()

    def test_technical_questions_not_forced_to_star(
        self, client: TestClient, auth_headers, resume_id, mock_interview
    ):
        technical = client.post(
            "/api/v1/interview/questions",
            json={"session_type": "technical", "resume_id": resume_id},
            headers=auth_headers,
        ).json()
        assert any(not q["star_applicable"] for q in technical["questions"])


class TestQuestionPool:
    def test_pool_covers_all_session_types(self):
        assert set(QUESTION_POOL) == set(SessionType)

    def test_pool_has_enough_questions(self):
        for session_type, pool in QUESTION_POOL.items():
            assert len(pool) >= POOL_SAMPLE_SIZE, session_type

    def test_behavioral_pool_is_star_shaped(self):
        for question, _ in QUESTION_POOL[SessionType.BEHAVIORAL]:
            assert any(m in question.lower() for m in ("anlatın", "paylaşın"))


class TestCvGroundingGuard:
    """Agent, CV'ye atıf yapan soru üretilmediyse hata vermeli."""

    def test_detects_grounded_question(self):
        questions = [
            q("FastAPI ile authentication'ı nasıl kurguladınız?", "FastAPI",
              QuestionSource.CV_SPECIFIC, False)
        ]
        assert has_cv_grounded_question(questions, CV_CONTENT)

    def test_rejects_ungrounded_questions(self):
        questions = [
            q("Kendinizden bahseder misiniz?", "Tanışma", QuestionSource.GENERAL, False),
            q("Takım çalışmasına bakışınız nedir?", "Genel",
              QuestionSource.CV_SPECIFIC, False),
        ]
        assert not has_cv_grounded_question(questions, CV_CONTENT)

    def test_general_source_does_not_count_as_grounding(self):
        questions = [
            q("FastAPI hakkında ne düşünüyorsunuz?", "FastAPI",
              QuestionSource.GENERAL, False)
        ]
        assert not has_cv_grounded_question(questions, CV_CONTENT)

    def test_agent_raises_when_no_cv_reference(self, monkeypatch):
        import app.agents.interview_agent as module
        from app.agents.interview_agent import InterviewAgentError

        ungrounded = InterviewQuestionSet(
            questions=[
                q("Kendinizden bahseder misiniz?", "Tanışma", QuestionSource.GENERAL, False)
            ]
        )

        monkeypatch.setattr(module.llm, "parse_structured", lambda *a, **kw: ungrounded)

        with pytest.raises(InterviewAgentError, match="atıfta bulunan soru"):
            module.generate_questions(SessionType.HR, CV_CONTENT)

    def test_agent_forces_star_for_behavioral(self, monkeypatch):
        import app.agents.interview_agent as module

        result = InterviewQuestionSet(
            questions=[
                q("FastAPI ile yaşadığınız bir sorunu anlatın.", "FastAPI",
                  QuestionSource.CV_SPECIFIC, False),  # model yanlış işaretledi
            ]
        )

        monkeypatch.setattr(module.llm, "parse_structured", lambda *a, **kw: result)

        out = module.generate_questions(SessionType.BEHAVIORAL, CV_CONTENT)
        assert out.questions[0].star_applicable is True


class TestPersistenceAndNotes:
    def test_session_is_retrievable(self, client: TestClient, auth_headers, session):
        resp = client.get(f"/api/v1/interview/sessions/{session['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["questions"]) == len(session["questions"])

    def test_sessions_listed(self, client: TestClient, auth_headers, session):
        resp = client.get("/api/v1/interview/sessions", headers=auth_headers)
        assert resp.status_code == 200
        assert any(s["id"] == session["id"] for s in resp.json())

    def test_save_star_note(self, client: TestClient, auth_headers, session):
        question = session["questions"][0]
        note = (
            "Durum: Ekipte mimari tercih ayrılığı vardı.\n"
            "Görev: Ortak bir karara varmak.\n"
            "Eylem: İki seçeneği prototipleyip ölçtüm.\n"
            "Sonuç: Ekip verilere dayanarak karar verdi."
        )
        resp = client.patch(
            f"/api/v1/interview/sessions/{session['id']}/questions/{question['id']}",
            json={"answer": note},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["answer"] == note

        again = client.get(
            f"/api/v1/interview/sessions/{session['id']}", headers=auth_headers
        ).json()
        saved = next(q for q in again["questions"] if q["id"] == question["id"])
        assert saved["answer"] == note

    def test_unknown_question_404(self, client: TestClient, auth_headers, session):
        resp = client.patch(
            f"/api/v1/interview/sessions/{session['id']}/questions/99999",
            json={"answer": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_other_user_cannot_access(self, client: TestClient, auth_headers, session):
        other = {"email": "other@example.com", "password": "sifre1234"}
        token = register_and_login(client, other)
        resp = client.get(
            f"/api/v1/interview/sessions/{session['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
