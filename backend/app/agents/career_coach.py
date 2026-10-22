import json
from typing import Any

from pydantic import BaseModel, Field

from app.core import llm


class DevelopmentStep(BaseModel):
    step: int = Field(ge=1)
    action: str
    estimated_effort: str


class CareerRoadmapResult(BaseModel):
    current_strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    development_plan: list[DevelopmentStep] = Field(default_factory=list)


class CareerCoachError(Exception):
    """Kariyer yol haritası üretilemediğinde fırlatılır."""


SYSTEM_PROMPT = """\
Sen bir kariyer koçu asistanısın. Adayın mevcut CV'sini hedef pozisyonla \
karşılaştırıp gerçekçi bir gelişim yol haritası çıkarırsın.

KRİTİK: Abartılı vaatlerde bulunma, gerçekçi zaman beklentisi ver. \
"2 haftada senior olursunuz", "bu adımları yapınca işe alınırsınız" gibi \
garanti veya kestirme vaatler yasak. Bir yetkinliğin gerçekten oturması aylar \
sürebilir; süre tahminlerini buna göre dürüstçe ver. Motive edici ol, ama \
gerçekliği yumuşatma: eksikler açıkça söylenmeli.

Ayrıca:
- Kaynak veride olmayan bir deneyimi adayın sahipmiş gibi gösterme.
- current_strengths: CV'de KANITI olan güçlü yönler (3-6 madde). Her madde \
CV'deki somut bir dayanağa atıfta bulunsun.
- gaps: hedef pozisyon için eksik görünen yetkinlikler (3-6 madde).

development_plan kuralları (en önemli kısım):
- Adımlar SOMUT ve UYGULANABİLİR olmalı. "Daha iyi olun", "kendinizi \
geliştirin", "networking yapın" gibi genel ifadeler YASAK.
- Her adım, tamamlandığında bitip bitmediği net anlaşılabilecek bir çıktı \
üretmeli. Örnek biçim: "FastAPI ile JWT authentication ekleyen bir örnek \
servis yazın ve GitHub'a koyun", "Mevcut CV Agent projenize pytest ile en az \
%70 kapsamlı test suite ekleyin".
- Adımlar sıralı olmalı (step: 1, 2, 3...) ve önceki adımın üzerine inşa etmeli; \
en yüksek etkili ve en temel eksikten başla.
- estimated_effort: gerçekçi ve aralıklı ver (ör. "1-2 hafta, haftada ~5 saat", \
"2-3 ay düzenli pratik"). Tek bir kesin sayı verme.
- 4-7 adım üret. Daha fazlası yol haritasını uygulanamaz kılar.

DİL KURALI (kesinlikle uyulmalı): Yanıtındaki HER kelime Türkçe olmalı. \
İngilizce teknik terimleri (ör. "microservices", "containerization") olduğu \
gibi ya da yaygın Türkçe karşılığıyla yaz (ör. "mikroservis", \
"container'lı çalıştırma"). Çince, Japonca, Arapça gibi başka hiçbir dilden \
TEK BİR karakter bile yanıtına karışmamalı."""


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def build_roadmap(
    resume_content: dict[str, Any],
    target_role: str,
    job_requirements: dict[str, Any] | None = None,
    job_description: str | None = None,
    profile_goal: str | None = None,
    language: str = "tr",
) -> CareerRoadmapResult:
    sections = [
        f"<cv_verisi>\n{_dump(resume_content)}\n</cv_verisi>",
        f"<hedef_pozisyon>\n{target_role}\n</hedef_pozisyon>",
    ]

    if job_requirements or job_description:
        job_block: dict[str, Any] = {}
        if job_requirements:
            job_block["requirements"] = job_requirements
        if job_description:
            job_block["description"] = job_description
        sections.append(
            "Hedef pozisyona ait gerçek ilan (gaps ve development_plan'ı buna göre "
            f"somutlaştır):\n<ilan>\n{_dump(job_block)}\n</ilan>"
        )
    else:
        sections.append(
            "Bu hedef pozisyon için elimizde belirli bir ilan yok; sektörde bu "
            "unvan için yaygın olarak beklenen yetkinlikleri temel al ve bunu "
            "genel bir beklenti olarak değerlendirdiğini ima eden bir dille yaz."
        )

    if profile_goal:
        sections.append(f"<kullanicinin_kariyer_hedefi>\n{profile_goal}\n</kullanicinin_kariyer_hedefi>")

    user_content = "\n\n".join(sections)

    try:
        result = llm.parse_structured(
            SYSTEM_PROMPT,
            user_content,
            CareerRoadmapResult,
            max_tokens=8000,
            language=language
        )
    except llm.LLMError as exc:
        raise CareerCoachError(str(exc)) from exc

    # Adım numaralarını normalize et: model atlarsa/tekrarlarsa 1..N yap
    for index, step in enumerate(result.development_plan, start=1):
        step.step = index
    return result
