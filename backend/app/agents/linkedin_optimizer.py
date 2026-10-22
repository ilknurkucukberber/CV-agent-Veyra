import json
import logging
from typing import Any

from app.agents.linkedin_schema import (
    CHECKLIST_ITEMS,
    HEADLINE_MAX_LENGTH,
    LinkedInOptimization,
)
from app.core import llm

logger = logging.getLogger(__name__)


class LinkedInAgentError(Exception):
    """LinkedIn optimizasyonu üretilemediğinde fırlatılır."""


SYSTEM_PROMPT = f"""\
Sen bir LinkedIn profil optimizasyonu asistanısın. Adayın CV verisinden \
LinkedIn profilinde kullanabileceği içerikler üretirsin.

KRİTİK KURAL: Kaynak veride olmayan hiçbir beceri, deneyim veya sayısal sonuç \
ekleme. Ölçülebilir bir sonuç kaynak veride yoksa sayı uydurma — niteliksel \
biçimde ifade et.

suggested_skills kuralı (özellikle dikkat et):
- SADECE (a) CV'de zaten geçen beceriler ve (b) CV'deki bir beceriden makul \
çıkarım yapılabilecek, hedef pozisyonla doğrudan ilgili YAKIN beceriler.
- Örnek: aday FastAPI biliyorsa "REST APIs" önerilebilir (FastAPI'nin doğrudan \
kullanım alanı). Ancak CV'de hiçbir container/orkestrasyon izi yoksa \
"Kubernetes" ÖNERİLEMEZ — bu yeni bir yetkinlik iddiası olur.
- Şüphedeysen önerme. Listeyi şişirmek yerine dar ve savunulabilir tut.

headline_options kuralı:
- Tam olarak 3 alternatif üret.
- Her biri en fazla {HEADLINE_MAX_LENGTH} karakter olmalı (LinkedIn sınırı). \
Bu sınırı ASLA aşma; yazdıktan sonra karakter sayısını kontrol et.
- Alternatifler birbirinden farklı yaklaşımlar sunsun (ör. biri unvan+teknoloji \
odaklı, biri değer/etki odaklı, biri hedef pozisyona yönelmiş).

about_section kuralı:
- 3-5 paragraf, birinci tekil şahıs, akıcı ve doğal bir dille yaz. \
Paragrafları boş satırla ayır.
- KLİŞELERDEN KAÇIN: "çalışkanım", "disiplinliyim", "takım oyuncusuyum", \
"detay odaklıyım", "hızlı öğrenirim", "kendimi geliştirmeye açığım" gibi \
kanıtlanamayan öz-nitelemeler kullanma. Bunun yerine CV'deki somut işi, \
teknolojiyi ve çıktıyı anlat — nitelik, örnekten kendiliğinden anlaşılsın.
- Abartılı pazarlama dili ("tutkulu", "uzman", "lider") yerine yaptığın işi \
sade biçimde tarif et.

experience_descriptions kuralı:
- CV'deki her deneyim için bir kayıt üret; role alanı CV'deki unvanla aynı olsun.
- linkedin_version: CV'nin kuru maddelerinden farklı olarak LinkedIn'e uygun, \
biraz daha akıcı ve okunur bir anlatım — ama içerik yine yalnızca kaynaktan.

profile_completeness_checklist kuralı:
- Şu maddeleri aynı sırayla değerlendir: {", ".join(CHECKLIST_ITEMS)}
- present: CV verisinde karşılığı varsa true, açıkça yoksa false, CV'den \
anlaşılamayacak bir şeyse (ör. profil fotoğrafı, banner, özel profil URL'si) null.
Tüm metinleri Türkçe yaz."""


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _truncate_headline(headline: str) -> str:
    """220 karakteri aşan başlığı kelime sınırında kısaltır.

    Model kuralı ihlal ederse kullanıcıya LinkedIn'in reddedeceği bir metin
    göstermemek için son savunma hattı.
    """
    if len(headline) <= HEADLINE_MAX_LENGTH:
        return headline
    logger.warning(
        "Model %d karakterlik headline üretti; %d karakter sınırına kısaltılıyor.",
        len(headline),
        HEADLINE_MAX_LENGTH,
    )
    cut = headline[: HEADLINE_MAX_LENGTH - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:-") + "…"


def optimize_profile(
    resume_content: dict[str, Any],
    target_role: str | None = None,
    job_requirements: dict[str, Any] | None = None,
    language: str = "tr",
) -> LinkedInOptimization:
    sections = [f"<cv_verisi>\n{_dump(resume_content)}\n</cv_verisi>"]
    if target_role:
        sections.append(f"<hedef_pozisyon>\n{target_role}\n</hedef_pozisyon>")
    if job_requirements:
        sections.append(
            "Hedef pozisyona ait ilan gereksinimleri (yalnızca CV'de karşılığı olan "
            f"veya yakın çıkarım yapılabilen beceriler için kullan):\n"
            f"<ilan_gereksinimleri>\n{_dump(job_requirements)}\n</ilan_gereksinimleri>"
        )

    user_content = "\n\n".join(sections)

    try:
        result = llm.parse_structured(
            SYSTEM_PROMPT, user_content, LinkedInOptimization, max_tokens=16000, language=language
        )
    except llm.LLMError as exc:
        raise LinkedInAgentError(str(exc)) from exc

    result.headline_options = [_truncate_headline(h) for h in result.headline_options]
    return result
