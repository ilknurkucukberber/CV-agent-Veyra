import json
from typing import Any

from app.agents.ats_schema import CATEGORY_WEIGHTS, AtsAnalysisResult
from app.core import llm
from app.models import JobPosting

DISCLAIMER = (
    "Bu skor, gerçek bir şirket ATS sisteminin sonucu değildir, "
    "uygulamanın kendi tahmini değerlendirmesidir."
)

SYSTEM_PROMPT = f"""\
Sen bir CV değerlendirme asistanısın. Yapılandırılmış CV verisini ATS (başvuru \
takip sistemi) uyumluluğu ve genel kalite açısından puanlarsın.

KRİTİK: Bu skor, gerçek bir şirket ATS sisteminin sonucu değildir, uygulamanın \
kendi tahmini değerlendirmesidir. Kullanıcıya sunulan her çıktıda bu \
netleştirilmelidir; değerlendirmeni bu çerçevede, iddialı kesinlik dili \
kullanmadan yap.

Kategoriler ve maksimum puanlar (toplam 100):
- format_readability (Biçim ve okunabilirlik): {CATEGORY_WEIGHTS['format_readability']}
- contact_info (İletişim ve temel bilgiler): {CATEGORY_WEIGHTS['contact_info']}
- experience_quality (Deneyim açıklamaları): {CATEGORY_WEIGHTS['experience_quality']}
- technical_skills (Teknik beceriler): {CATEGORY_WEIGHTS['technical_skills']}
- keyword_match (Anahtar kelime uyumu): {CATEGORY_WEIGHTS['keyword_match']}
- projects_achievements (Projeler ve başarılar): {CATEGORY_WEIGHTS['projects_achievements']}
- language_quality (Dil ve yazım kalitesi): {CATEGORY_WEIGHTS['language_quality']}

Kurallar:
- Her kategori puanı 0 ile o kategorinin maksimumu arasında olmalı.
- total_score, kategori puanlarının toplamına eşit olmalı.
- Hedef pozisyon verildiyse keyword_match'i ilanın gereksinimlerine göre puanla.
  Hedef pozisyon verilmediyse keyword_match'i kişinin CV'sinden anlaşılan hedef \
role göre genel değerlendir; bu durumu ilgili gap/strength maddelerinde belirt.
- strengths: CV'nin somut güçlü yönleri (3-6 madde).
- gaps: her eksik için issue (sorun), why_it_matters (neden önemli) ve \
how_to_fix (somut, uygulanabilir düzeltme önerisi) alanlarını doldur.
- Tüm metinleri Türkçe yaz."""


class AtsAnalysisError(Exception):
    """ATS analizi başarısız olduğunda fırlatılır."""


def _clamp_and_reconcile(result: AtsAnalysisResult) -> AtsAnalysisResult:
    """Kategori puanlarını ağırlık sınırına kırpar ve toplamı garanti eder."""
    scores = result.category_scores
    for field, weight in CATEGORY_WEIGHTS.items():
        value = getattr(scores, field)
        setattr(scores, field, max(0, min(weight, value)))
    result.total_score = sum(getattr(scores, f) for f in CATEGORY_WEIGHTS)
    return result


def analyze_resume(
    parsed_json: dict[str, Any],
    structure_analysis: dict[str, Any] | None,
    job_posting: JobPosting | None = None,
    language: str = "tr",
) -> AtsAnalysisResult:
    sections = [
        "Aşağıdaki yapılandırılmış CV verisini değerlendir.",
        f"<cv_verisi>\n{json.dumps(parsed_json, ensure_ascii=False, indent=2)}\n</cv_verisi>",
    ]
    if structure_analysis:
        sections.append(
            "CV dosyasının yapısal analizi (biçim/okunabilirlik puanlamasında kullan):\n"
            f"<yapisal_analiz>\n{json.dumps(structure_analysis, ensure_ascii=False, indent=2)}\n</yapisal_analiz>"
        )
    if job_posting is not None:
        job_info = {
            "title": job_posting.title,
            "company": job_posting.company,
            "description": job_posting.description,
            "requirements": job_posting.requirements,
        }
        sections.append(
            "Hedef pozisyon (keyword_match'i buna göre puanla):\n"
            f"<hedef_pozisyon>\n{json.dumps(job_info, ensure_ascii=False, indent=2)}\n</hedef_pozisyon>"
        )
    else:
        sections.append("Hedef pozisyon verilmedi.")

    user_content = "\n\n".join(sections)

    try:
        result = llm.parse_structured(
            SYSTEM_PROMPT, 
            user_content, 
            AtsAnalysisResult, 
            max_tokens=8000, 
            language=language
        )
    except llm.LLMError as exc:
        raise AtsAnalysisError(str(exc)) from exc

    return _clamp_and_reconcile(result)
