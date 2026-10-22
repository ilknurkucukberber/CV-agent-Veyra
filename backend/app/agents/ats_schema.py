from pydantic import BaseModel, Field

# Kategori -> maksimum puan (toplam 100)
CATEGORY_WEIGHTS: dict[str, int] = {
    "format_readability": 15,       # Biçim ve okunabilirlik
    "contact_info": 10,             # İletişim ve temel bilgiler
    "experience_quality": 20,       # Deneyim açıklamaları
    "technical_skills": 15,         # Teknik beceriler
    "keyword_match": 20,            # Anahtar kelime uyumu
    "projects_achievements": 15,    # Projeler ve başarılar
    "language_quality": 5,          # Dil ve yazım kalitesi
}

CATEGORY_LABELS: dict[str, str] = {
    "format_readability": "Biçim ve okunabilirlik",
    "contact_info": "İletişim ve temel bilgiler",
    "experience_quality": "Deneyim açıklamaları",
    "technical_skills": "Teknik beceriler",
    "keyword_match": "Anahtar kelime uyumu",
    "projects_achievements": "Projeler ve başarılar",
    "language_quality": "Dil ve yazım kalitesi",
}


class CategoryScores(BaseModel):
    format_readability: int = Field(ge=0, le=15)
    contact_info: int = Field(ge=0, le=10)
    experience_quality: int = Field(ge=0, le=20)
    technical_skills: int = Field(ge=0, le=15)
    keyword_match: int = Field(ge=0, le=20)
    projects_achievements: int = Field(ge=0, le=15)
    language_quality: int = Field(ge=0, le=5)


class AtsGap(BaseModel):
    issue: str
    why_it_matters: str
    how_to_fix: str


class AtsAnalysisResult(BaseModel):
    total_score: int = Field(ge=0, le=100)
    category_scores: CategoryScores
    strengths: list[str] = Field(default_factory=list)
    gaps: list[AtsGap] = Field(default_factory=list)
