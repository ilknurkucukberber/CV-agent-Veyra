import pytest
from fastapi.testclient import TestClient

from app.agents.interview_evaluator import (
    AnswerEvaluation,
    AnswerFeedback,
    find_invented_numbers,
    find_judgmental_language,
)
from tests.fixtures import register_and_login
from tests.test_interview import mock_interview, resume_id  # noqa: F401  (fixtures)

# Kullanıcının verdiği zayıf cevap: somut olay yok, teknik detay yok
WEAK_ANSWER = "Bir keresinde bir ekip arkadaşımla anlaşamadık ama sonunda hallettik."

# Bu cevaba karşılık gelen yapıcı, kaynakla sınırlı değerlendirme
WEAK_EVALUATION = AnswerEvaluation(
    feedback=AnswerFeedback(
        too_general=True,
        missing_technical_detail=True,
        missing_position_connection=True,
        structure_notes=(
            "Cevap STAR akışının yalnızca Durum kısmına değiniyor. Anlaşmazlığın "
            "hangi konuda olduğu, sizin sorumluluğunuzun ne olduğu ve hangi adımları "
            "attığınız belirtilmemiş. 'Sonunda hallettik' ifadesi sonucu somutlaştırmıyor; "
            "buraya ölçülebilir veya gözlemlenebilir bir sonuç ekleyebilirsiniz."
        ),
    ),
    suggested_improved_answer=(
        "Durum: Bir ekip arkadaşımla bir konuda görüş ayrılığı yaşadık. "
        "[anlaşmazlığın konusunu yazın]\n"
        "Görev: [bu durumda sizin sorumluluğunuz neydi]\n"
        "Eylem: [anlaşmazlığı çözmek için attığınız adımları yazın]\n"
        "Sonuç: Anlaşmazlığı çözdük. [sonucun ekibe/işe etkisini ekleyin]"
    ),
    follow_up_question="Bu süreçte karşı tarafın bakış açısını anlamak için ne yaptınız?",
)


@pytest.fixture()
def mock_evaluator(monkeypatch):
    calls: list[dict] = []

    def fake(question, user_answer, star_applicable, session_type, job_title=None, job_requirements=None, language="tr"):
        calls.append(
            {
                "question": question,
                "user_answer": user_answer,
                "star_applicable": star_applicable,
                "session_type": session_type,
                "job_title": job_title,
            }
        )
        return WEAK_EVALUATION.model_copy(deep=True)

    monkeypatch.setattr("app.api.routes.interview.evaluate_answer", fake)
    return calls


@pytest.fixture()
def session(client: TestClient, auth_headers, resume_id, mock_interview) -> dict:  # noqa: F811
    resp = client.post(
        "/api/v1/interview/questions",
        json={"session_type": "behavioral", "resume_id": resume_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def answer(client: TestClient, headers, session: dict, index: int, text: str):
    return client.post(
        f"/api/v1/interview/sessions/{session['id']}/answer",
        json={"question_id": session["questions"][index]["id"], "user_answer": text},
        headers=headers,
    )


class TestEndpoint:
    def test_requires_auth(self, client: TestClient, session):
        resp = client.post(
            f"/api/v1/interview/sessions/{session['id']}/answer",
            json={"question_id": session["questions"][0]["id"], "user_answer": "x"},
        )
        assert resp.status_code == 401

    def test_unknown_session_404(self, client: TestClient, auth_headers, mock_evaluator):
        resp = client.post(
            "/api/v1/interview/sessions/9999/answer",
            json={"question_id": 1, "user_answer": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_question_from_other_session_404(
        self, client: TestClient, auth_headers, session, mock_evaluator
    ):
        resp = client.post(
            f"/api/v1/interview/sessions/{session['id']}/answer",
            json={"question_id": 99999, "user_answer": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_empty_answer_rejected(
        self, client: TestClient, auth_headers, session, mock_evaluator
    ):
        resp = answer(client, auth_headers, session, 0, "")
        assert resp.status_code == 422

    def test_other_user_cannot_answer(
        self, client: TestClient, auth_headers, session, mock_evaluator
    ):
        other = {"email": "other@example.com", "password": "sifre1234"}
        token = register_and_login(client, other)
        resp = client.post(
            f"/api/v1/interview/sessions/{session['id']}/answer",
            json={"question_id": session["questions"][0]["id"], "user_answer": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_llm_unavailable_returns_503(
        self, client: TestClient, auth_headers, session, monkeypatch
    ):
        from app.agents.interview_evaluator import InterviewEvaluationError

        def boom(*args, **kwargs):
            raise InterviewEvaluationError("ANTHROPIC_API_KEY tanımlı değil")

        monkeypatch.setattr("app.api.routes.interview.evaluate_answer", boom)
        resp = answer(client, auth_headers, session, 0, WEAK_ANSWER)
        assert resp.status_code == 503


class TestEndToEndWeakAnswer:
    """Uçtan uca: soru sor → zayıf cevap ver → geri bildirimi doğrula."""

    @pytest.fixture()
    def result(self, client: TestClient, auth_headers, session, mock_evaluator) -> dict:
        resp = answer(client, auth_headers, session, 0, WEAK_ANSWER)
        assert resp.status_code == 201, resp.text
        return resp.json()

    def test_output_schema(self, result):
        assert set(result["feedback"]) == {
            "too_general",
            "missing_technical_detail",
            "missing_position_connection",
            "structure_notes",
        }
        assert isinstance(result["suggested_improved_answer"], str)
        assert result["follow_up_question"] is None or isinstance(
            result["follow_up_question"], str
        )

    def test_weak_answer_flagged_as_general(self, result):
        assert result["feedback"]["too_general"] is True
        assert result["feedback"]["missing_technical_detail"] is True

    def test_feedback_is_constructive_not_judgmental(self, result):
        notes = result["feedback"]["structure_notes"]
        assert len(notes) > 50, "Geri bildirim somut olacak kadar uzun olmalı"
        # Kişiye dönük yargı içermemeli
        assert not find_judgmental_language(notes)
        # Ne eksik olduğunu söylemeli
        assert any(k in notes.lower() for k in ("belirtilmemiş", "ekleyebilirsiniz", "değinmiyor"))

    def test_improved_answer_invents_no_numbers(self, result):
        """KRİTİK: geliştirilmiş cevap kaynakta olmayan metrik uydurmamalı."""
        invented = find_invented_numbers(
            result["user_answer"], result["suggested_improved_answer"]
        )
        assert not invented, f"Uydurulmuş sayı(lar): {invented}"

    def test_improved_answer_uses_placeholders_not_fabrication(self, result):
        """Kullanıcı detay vermediyse uydurmak yerine yer tutucu kullanılmalı."""
        improved = result["suggested_improved_answer"]
        assert "[" in improved and "]" in improved
        # Kaynakta geçmeyen somut bir proje/teknoloji adı eklenmemeli
        for invented in ("FastAPI", "PostgreSQL", "Kubernetes", "Acme"):
            assert invented not in improved

    def test_answer_persisted(self, client: TestClient, auth_headers, session, result):
        stored = client.get(
            f"/api/v1/interview/sessions/{session['id']}", headers=auth_headers
        ).json()
        question = next(
            q for q in stored["questions"] if q["id"] == result["question_id"]
        )
        assert question["answer"] == WEAK_ANSWER
        assert question["evaluation"]["feedback"]["too_general"] is True
        assert question["evaluation"]["suggested_improved_answer"]

    def test_evaluator_receives_question_context(self, result, mock_evaluator, session):
        call = mock_evaluator[0]
        assert call["question"] == session["questions"][0]["question"]
        assert call["user_answer"] == WEAK_ANSWER
        assert call["star_applicable"] is True
        assert call["session_type"] == "behavioral"


class TestSessionFlow:
    def test_next_question_pointer_advances(
        self, client: TestClient, auth_headers, session, mock_evaluator
    ):
        first = answer(client, auth_headers, session, 0, WEAK_ANSWER).json()
        assert first["next_question_id"] == session["questions"][1]["id"]
        assert first["remaining_questions"] == len(session["questions"]) - 1

        second = answer(client, auth_headers, session, 1, WEAK_ANSWER).json()
        assert second["next_question_id"] == session["questions"][2]["id"]
        assert second["remaining_questions"] == len(session["questions"]) - 2

    def test_status_transitions_to_in_progress(
        self, client: TestClient, auth_headers, session, mock_evaluator
    ):
        answer(client, auth_headers, session, 0, WEAK_ANSWER)
        stored = client.get(
            f"/api/v1/interview/sessions/{session['id']}", headers=auth_headers
        ).json()
        assert stored["status"] == "in_progress"

    def test_session_completes_after_all_answers(
        self, client: TestClient, auth_headers, session, mock_evaluator
    ):
        for index in range(len(session["questions"])):
            resp = answer(client, auth_headers, session, index, WEAK_ANSWER)
            assert resp.status_code == 201

        assert resp.json()["next_question_id"] is None
        assert resp.json()["remaining_questions"] == 0
        stored = client.get(
            f"/api/v1/interview/sessions/{session['id']}", headers=auth_headers
        ).json()
        assert stored["status"] == "completed"

    def test_reanswering_updates_evaluation(
        self, client: TestClient, auth_headers, session, mock_evaluator
    ):
        answer(client, auth_headers, session, 0, WEAK_ANSWER)
        answer(client, auth_headers, session, 0, "Daha detaylı ikinci cevabım.")
        stored = client.get(
            f"/api/v1/interview/sessions/{session['id']}", headers=auth_headers
        ).json()
        question = stored["questions"][0]
        assert question["answer"] == "Daha detaylı ikinci cevabım."


class TestFabricationGuards:
    """Sunucu tarafı denetim yardımcılarının doğruluğu."""

    def test_detects_invented_metric(self):
        user = "Sorguları optimize ettim ve sistem hızlandı."
        improved = "Sorguları optimize ederek yanıt süresini %40 azalttım."
        assert find_invented_numbers(user, improved) == ["40"]

    def test_allows_numbers_present_in_source(self):
        user = "3 kişilik bir ekipte çalıştım ve süreyi 2 güne indirdim."
        improved = "3 kişilik ekipte süreci 2 güne indirdim."
        assert find_invented_numbers(user, improved) == []

    def test_no_numbers_anywhere_is_clean(self):
        assert find_invented_numbers("Bir sorunu çözdüm.", "Bir sorunu şöyle çözdüm.") == []

    def test_detects_judgmental_language(self):
        assert find_judgmental_language("Bu aday dürüst değil gibi görünüyor.")
        assert find_judgmental_language("Bu pozisyona uygun değilsiniz.")

    def test_constructive_language_passes(self):
        assert not find_judgmental_language(
            "Cevabınızda Eylem bölümü eksik; attığınız adımları ekleyebilirsiniz."
        )

    def test_agent_logs_but_does_not_fail_on_invented_number(self, monkeypatch, caplog):
        """Uydurma sayı tespit edilirse loglanmalı, istek düşmemeli."""
        import app.agents.interview_evaluator as module

        bad = AnswerEvaluation(
            feedback=AnswerFeedback(
                too_general=False,
                missing_technical_detail=False,
                missing_position_connection=False,
                structure_notes="Yapı iyi.",
            ),
            suggested_improved_answer="Yanıt süresini %40 azalttım.",
            follow_up_question=None,
        )

        monkeypatch.setattr(module.llm, "parse_structured", lambda *a, **kw: bad)

        with caplog.at_level("WARNING"):
            result = module.evaluate_answer("Soru?", "Optimize ettim.", True, "technical")
        assert result.suggested_improved_answer
        assert "kaynakta olmayan sayı" in caplog.text
