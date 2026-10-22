import json
from typing import Any

from app.agents.job_schema import JobMatchResult, JobRequirements
from app.core import llm

EXTRACT_SYSTEM_PROMPT = """\
Sen bir iş ilanı ayrıştırma asistanısın. Verilen ilan metnini istenen JSON \
şemasına dönüştürürsün.

KRİTİK KURAL: İlanda açıkça belirtilmeyen hiçbir gereksinimi çıkarma veya \
uydurma. Emin olmadığın alanları null bırak, listelerde yalnızca metinde \
açıkça geçen öğeler olsun.

Alan rehberi:
- required_skills: "zorunlu", "aranan", "must have" olarak geçen beceriler.
- preferred_skills: "tercihen", "artı olur", "nice to have" olarak geçenler.
- experience_years: ilanda yazıldığı biçimde aktar (ör. "3-5 yıl", "en az 2 yıl").
- programming_languages: yalnızca programlama dilleri (Python, Java, Go...).
- tools_and_technologies: framework, veritabanı, araç ve platformlar.
- key_responsibilities: pozisyonun temel sorumlulukları, kısa maddeler halinde.
Metinler ilanın dilinde kalsın."""

MATCH_SYSTEM_PROMPT = """\
Sen bir kariyer danışmanı asistanısın. Bir adayın CV verisiyle bir iş ilanının \
gereksinimlerini karşılaştırıp eşleşme değerlendirmesi üretirsin.

KRİTİK KURAL: Eksik beceriyi kullanıcının CV'sine otomatik ekleme veya \
"ekleyelim" diye önerme. Bunun yerine "bu pozisyon için X önemli görünüyor, \
öğrenmeniz eşleşme oranınızı artırabilir" şeklinde çerçevele.

improvement_suggestions kuralları (çok önemli):
- Öneriler SADECE kullanıcının CV'sinde zaten var olabilecek ama net \
yazılmamış deneyimleri daha görünür kılmaya yönelik olmalıdır.
- Kullanıcının o deneyime sahip olduğunu VARSAYMA; koşullu dil kullan: \
"Docker kullandıysanız proje açıklamanıza ekleyin", "Bu araçla çalıştıysanız \
deneyim maddesinde belirtin" gibi.
- Kullanıcının sahip olmadığı bir beceriyi CV'ye yazmasını asla önerme.
- Öğrenme tavsiyesi verirken bunu bir CV düzenleme önerisi gibi değil, \
gelişim önerisi olarak yaz ve eşleşme oranına etkisi üzerinden çerçevele.

Puanlama:
- match_percentage: 0-100 arası tam sayı. required_skills'e preferred_skills'ten \
belirgin biçimde daha fazla ağırlık ver; deneyim süresi ve eğitim uyumunu da \
hesaba kat.
- matched_skills: CV'de karşılığı AÇIKÇA bulunan ilan becerileri.
- missing_skills: ilanda istenen ama CV'de karşılığı görünmeyen beceriler.
Tüm metinleri Türkçe yaz."""


class JobAgentError(Exception):
    """İlan çıkarma veya eşleştirme başarısız olduğunda fırlatılır."""


def _parse_structured(system: str, user_content: str, output_model, max_tokens: int, what: str, language: str = "tr"):
    try:
        return llm.parse_structured(system, user_content, output_model, max_tokens=max_tokens, language=language)
    except llm.LLMError as exc:
        raise JobAgentError(f"{exc} ({what})") from exc


def extract_requirements(job_text: str, language: str = "tr") -> JobRequirements:
    return _parse_structured(
        EXTRACT_SYSTEM_PROMPT,
        f"<ilan_metni>\n{job_text}\n</ilan_metni>",
        JobRequirements,
        max_tokens=8000,
        what="ilan çıkarma",
        language=language,
    )


def match_resume_to_job(
    resume_content: dict[str, Any],
    job_title: str,
    requirements: dict[str, Any] | None,
    job_description: str | None,
    language: str = "tr",
) -> JobMatchResult:
    job_block: dict[str, Any] = {"title": job_title}
    if requirements:
        job_block["requirements"] = requirements
    if job_description:
        job_block["description"] = job_description

    content = (
        f"<cv_verisi>\n{json.dumps(resume_content, ensure_ascii=False, indent=2)}\n</cv_verisi>\n\n"
        f"<ilan>\n{json.dumps(job_block, ensure_ascii=False, indent=2)}\n</ilan>"
    )

    result = _parse_structured(
        MATCH_SYSTEM_PROMPT, content, JobMatchResult, max_tokens=8000, what="eşleştirme", language=language
    )
    result.match_percentage = max(0, min(100, result.match_percentage))
    return result
