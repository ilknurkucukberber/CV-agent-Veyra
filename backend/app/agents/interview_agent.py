import json
import re
from typing import Any

from app.agents.interview_schema import (
    POOL_SAMPLE_SIZE,
    QUESTION_POOL,
    InterviewQuestionSet,
    QuestionSource,
    SessionType,
)
from app.core import llm

SESSION_TYPE_LABELS = {
    SessionType.HR: "İK / ön görüşme",
    SessionType.TECHNICAL: "Teknik görüşme",
    SessionType.BEHAVIORAL: "Davranışsal (yetkinlik bazlı) görüşme",
}


class InterviewAgentError(Exception):
    """Görüşme soruları üretilemediğinde fırlatılır."""


SYSTEM_PROMPT = """\
Sen bir mülakat hazırlık asistanısın. Adayın CV'sine ve (varsa) hedef ilana \
göre görüşme soruları üretirsin.

KRİTİK KURAL: Kaynak veride olmayan bir deneyimi varmış gibi soru sorma. \
"X projenizdeki Kubernetes kullanımını anlatın" gibi bir soru ancak CV'de \
Kubernetes gerçekten geçiyorsa sorulabilir. Adayın sahip olmadığı bir \
yetkinliği ima eden soru üretme.

Üç kaynaktan soru üret ve her sorunun source alanını doğru işaretle:

1. source="general": Sana verilen sabit soru havuzundaki soruları HAFİFÇE \
çeşitlendir — anlamı ve amacı aynı kalsın, ifade biçimi doğallaşsın. Yeni \
konu ekleme, havuzdaki her soruya karşılık bir soru üret. category alanını \
havuzda verilen kategoriyle aynı tut.

2. source="cv_specific": Adayın CV'sindeki SOMUT projelerden, \
deneyimlerinden ve teknolojilerinden türetilmiş sorular. Soru metni, CV'de \
geçen gerçek bir teknoloji, proje adı veya şirket adına açıkça atıfta \
bulunmalı. Örnek biçim: "CV Agent projenizde FastAPI ile authentication'ı \
nasıl kurguladınız?" En az 3, en fazla 5 soru üret.

3. source="job_specific": Hedef ilan verildiyse, ilanda istenen \
teknoloji/araç/sorumluluklardan türetilmiş sorular. İlan verilmediyse bu \
kaynaktan hiç soru üretme. En fazla 4 soru üret.

STAR kuralı:
- Davranışsal sorular STAR (Durum-Görev-Eylem-Sonuç) formatında \
cevaplanabilir olmalı: geçmişte yaşanmış SOMUT bir olayı anlatmaya davet \
etsin ("...bir durumu anlatın", "...yaşadığınız bir örneği paylaşın"). \
Varsayımsal ("ne yapardınız") kalıbı kullanma.
- star_applicable: soru geçmiş bir deneyimi anlatmaya davet ediyorsa true, \
bilgi/görüş soran teknik ya da olgusal bir soruysa false.

category alanı kısa ve okunur bir Türkçe etiket olsun (ör. "Sistem tasarımı", \
"Çatışma yönetimi", "FastAPI"). Tüm metinleri Türkçe yaz."""


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _tokens(value: Any) -> set[str]:
    """CV içeriğindeki anlamlı kelimeleri (3+ harf) küçük harfli küme olarak döner."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return {w for w in re.findall(r"[\wğüşıöçĞÜŞİÖÇ]{3,}", text.lower())}


def _cv_reference_terms(resume_content: dict[str, Any]) -> set[str]:
    """CV'deki spesifik terimler: beceriler, şirketler, proje adları, teknolojiler."""
    terms: set[str] = set()
    for skill in resume_content.get("skills") or []:
        terms |= _tokens(skill)
    for exp in resume_content.get("experience") or []:
        terms |= _tokens(exp.get("company", "")) | _tokens(exp.get("role", ""))
        terms |= _tokens(exp.get("description", ""))
    for project in resume_content.get("projects") or []:
        terms |= _tokens(project.get("name", ""))
        for tech in project.get("technologies") or []:
            terms |= _tokens(tech)
    for cert in resume_content.get("certificates") or []:
        terms |= _tokens(cert)
    return terms


def has_cv_grounded_question(questions, resume_content: dict[str, Any]) -> bool:
    """CV'deki somut bir terime atıfta bulunan en az bir soru var mı?"""
    terms = _cv_reference_terms(resume_content)
    if not terms:
        return False
    for question in questions:
        if question.source != QuestionSource.CV_SPECIFIC:
            continue
        if _tokens(question.question) & terms:
            return True
    return False


def generate_questions(
    session_type: SessionType,
    resume_content: dict[str, Any],
    job_title: str | None = None,
    job_requirements: dict[str, Any] | None = None,
    language: str = "tr",
) -> InterviewQuestionSet:
    pool = QUESTION_POOL[session_type][:POOL_SAMPLE_SIZE]
    pool_block = "\n".join(f"- [{category}] {q}" for q, category in pool)

    sections = [
        f"Görüşme türü: {SESSION_TYPE_LABELS[session_type]}",
        f"<sabit_soru_havuzu>\n{pool_block}\n</sabit_soru_havuzu>",
        f"<cv_verisi>\n{_dump(resume_content)}\n</cv_verisi>",
    ]
    if job_title or job_requirements:
        job_block: dict[str, Any] = {}
        if job_title:
            job_block["title"] = job_title
        if job_requirements:
            job_block["requirements"] = job_requirements
        sections.append(f"<hedef_ilan>\n{_dump(job_block)}\n</hedef_ilan>")
    else:
        sections.append("Hedef ilan verilmedi; job_specific soru üretme.")

    user_content = "\n\n".join(sections)

    try:
        result = llm.parse_structured(
            SYSTEM_PROMPT, user_content, InterviewQuestionSet, max_tokens=10000, language=language
        )
    except llm.LLMError as exc:
        raise InterviewAgentError(str(exc)) from exc

    # İlan yoksa job_specific soru olmamalı
    if not (job_title or job_requirements):
        result.questions = [
            q for q in result.questions if q.source != QuestionSource.JOB_SPECIFIC
        ]

    # Davranışsal görüşmede geçmiş deneyim soruları STAR ile cevaplanabilir olmalı
    if session_type == SessionType.BEHAVIORAL:
        for question in result.questions:
            if question.source in (QuestionSource.GENERAL, QuestionSource.CV_SPECIFIC):
                question.star_applicable = True

    if not result.questions:
        raise InterviewAgentError("Model hiç soru üretmedi.")
    if not has_cv_grounded_question(result.questions, resume_content):
        raise InterviewAgentError(
            "CV'deki somut bir teknoloji veya projeye atıfta bulunan soru üretilemedi."
        )

    return result
