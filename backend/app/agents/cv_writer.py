import json
from typing import Any

from pydantic import BaseModel, Field

from app.agents.resume_schema import ParsedResume
from app.core import llm
from app.models import JobPosting, Profile
from app.models.enums import EditLevel


class RewrittenResume(ParsedResume):
    """CV içeriği + from_scratch modunda üretilen profesyonel özet."""

    summary: str | None = None


class ChangeLogEntry(BaseModel):
    section: str
    before: str
    after: str
    reason: str


class RewriteResult(BaseModel):
    updated_content: RewrittenResume
    change_log: list[ChangeLogEntry] = Field(default_factory=list)


class CvRewriteError(Exception):
    """CV yeniden yazımı başarısız olduğunda fırlatılır."""


# Tüm seviyelerde geçerli ortak kurallar
COMMON_RULES = """\
KRİTİK KURAL: Kaynak veride olmayan hiçbir beceri, sayısal sonuç veya deneyim \
ekleme. Ölçülebilir bir sonuç kaynak veride yoksa, sayı uydurma — ya \
kullanıcıdan iste ya da niteliksel biçimde ifade et. (Kullanıcıdan istenecek \
bilgiyi change_log'daki reason alanında "kullanıcıdan istenmeli:" önekiyle belirt.)

Çıktı kuralları:
- updated_content, verilen CV şemasıyla aynı yapıda olmalı.
- change_log'a her önemli değişiklik için bir kayıt ekle: section (hangi bölüm, \
ör. "experience[0].description", "summary", "skills"), before (önceki metin; \
yeni eklenen bölümse boş string), after (yeni metin), reason (değişikliğin \
gerekçesi, Türkçe).
- Değiştirmediğin alanları updated_content'te aynen koru.
- Tüm metinler kaynak CV'nin dilinde kalsın (Türkçe CV -> Türkçe çıktı)."""

LIGHT_PROMPT = f"""\
Sen bir CV editörüsün. Görevin YALNIZCA hafif düzenleme (light edit):
- Yazım ve dilbilgisi hatalarını düzelt.
- Tekrarlanan ifadeleri temizle, gereksiz kelime kalabalığını sadeleştir.
- Bölüm içi madde sıralamasını iyileştir (en güçlü/en güncel öne).

YAPMA: Yeni içerik üretme, cümleleri yeniden yazma (hata düzeltme dışında), \
yeni beceri/deneyim/proje ekleme, bölüm ekleme-çıkarma. Sadece var olanı düzenle.
summary alanına dokunma; kaynakta yoksa null bırak.

{COMMON_RULES}"""

TARGETED_PROMPT = f"""\
Sen bir CV editörüsün. Görevin CV'yi verilen hedef iş ilanına göre optimize \
etmek (targeted edit):
- İlanın gereksinimleriyle örtüşen mevcut becerileri ve deneyimleri öne çıkar \
(sıralamayı değiştir, ilgili maddeleri güçlendir).
- İlanın anahtar kelimelerini mevcut cümlelere DOĞAL biçimde yerleştir — ama \
yalnızca o anahtar kelimenin karşılığı kaynak veride gerçekten varsa. Anahtar \
kelime listesi gibi yapay yığınlar oluşturma.
- İlanla ilgisiz bölümleri kısalt (tamamen silme, sadece sadeleştir).

YAPMA: Kaynakta olmayan beceri/araç/deneyim ekleme — ilan istiyor diye CV'ye \
yeni yetkinlik yazma. summary alanına dokunma; kaynakta yoksa null bırak.

{COMMON_RULES}"""

FROM_SCRATCH_PROMPT = f"""\
Sen bir CV yazarısın. Görevin, verilen profil ve CV verisini birleştirerek \
sıfırdan eksiksiz bir CV üretmek (from scratch):
- Şu bölümleri oluştur (kaynakta karşılığı olanları): Ad Soyad ve İletişim \
(personal_info), Profesyonel Özet (summary), Eğitim (education), Deneyim \
(experience), Projeler (projects), Beceriler (skills), Sertifikalar \
(certificates), Diller (languages).
- Profesyonel Özet'i YALNIZCA kaynak verideki gerçeklerden damıt; hedef, \
kişinin profilindeki kariyer hedefiyle uyumlu, 2-3 cümlelik güçlü bir özet.
- Profil ve CV verisi çelişirse daha güncel/detaylı olanı tercih et ve bunu \
change_log'da belirt.
- Deneyim açıklamalarını etki odaklı, fiille başlayan maddeler halinde yeniden \
yaz — ama içerik kaynaktan gelsin.

{COMMON_RULES}"""

PROMPTS: dict[EditLevel, str] = {
    EditLevel.LIGHT: LIGHT_PROMPT,
    EditLevel.TARGETED: TARGETED_PROMPT,
    EditLevel.FROM_SCRATCH: FROM_SCRATCH_PROMPT,
}


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def rewrite_resume(
    edit_level: EditLevel,
    source_content: dict[str, Any],
    profile: Profile | None = None,
    job_posting: JobPosting | None = None,
    language: str = "tr",
) -> RewriteResult:
    sections = [f"<kaynak_cv>\n{_dump(source_content)}\n</kaynak_cv>"]

    if edit_level == EditLevel.TARGETED and job_posting is not None:
        job_info = {
            "title": job_posting.title,
            "company": job_posting.company,
            "description": job_posting.description,
            "requirements": job_posting.requirements,
        }
        sections.append(f"<hedef_ilan>\n{_dump(job_info)}\n</hedef_ilan>")

    if edit_level == EditLevel.FROM_SCRATCH and profile is not None:
        profile_info = {
            "education_level": profile.education_level,
            "department": profile.department,
            "university": profile.university,
            "graduation_year": profile.graduation_year,
            "work_experience": profile.work_experience,
            "internship_experience": profile.internship_experience,
            "technical_skills": profile.technical_skills,
            "certificates": profile.certificates,
            "projects": profile.projects,
            "english_level": profile.english_level,
            "target_city": profile.target_city,
            "career_goal": profile.career_goal,
        }
        sections.append(f"<profil>\n{_dump(profile_info)}\n</profil>")

    system_prompt = PROMPTS[edit_level]
    user_content = "\n\n".join(sections)

    try:
        return llm.parse_structured(
            system_prompt, user_content, RewriteResult, max_tokens=16000, language=language
        )
    except llm.LLMError as exc:
        raise CvRewriteError(str(exc)) from exc
