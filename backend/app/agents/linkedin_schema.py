from pydantic import BaseModel, Field

# LinkedIn headline alanının karakter sınırı
HEADLINE_MAX_LENGTH = 220

# Profil eksiksizliği için kontrol edilen standart maddeler
CHECKLIST_ITEMS = [
    "Profil fotoğrafı",
    "Arka plan (banner) görseli",
    "Başlık (headline)",
    "Hakkında (about) bölümü",
    "Güncel pozisyon ve açıklaması",
    "Eğitim bilgisi",
    "Beceriler (en az 5 adet)",
    "Sertifikalar",
    "Diller",
    "Öne çıkan projeler",
    "Özel profil URL'si",
    "İletişim bilgileri",
]


class ExperienceDescription(BaseModel):
    role: str
    linkedin_version: str


class ChecklistItem(BaseModel):
    item: str
    # true: CV verisinde karşılığı var, false: yok,
    # null: CV'den anlaşılamaz (ör. profil fotoğrafı)
    present: bool | None = None


class LinkedInOptimization(BaseModel):
    headline_options: list[str] = Field(default_factory=list)
    about_section: str
    experience_descriptions: list[ExperienceDescription] = Field(default_factory=list)
    suggested_skills: list[str] = Field(default_factory=list)
    profile_completeness_checklist: list[ChecklistItem] = Field(default_factory=list)
