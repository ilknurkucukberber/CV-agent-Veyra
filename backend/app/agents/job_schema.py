from pydantic import BaseModel, Field


class JobRequirements(BaseModel):
    """İlan metninden çıkarılan yapılandırılmış gereksinimler."""

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_years: str | None = None
    programming_languages: list[str] = Field(default_factory=list)
    tools_and_technologies: list[str] = Field(default_factory=list)
    education_requirement: str | None = None
    language_requirement: str | None = None
    key_responsibilities: list[str] = Field(default_factory=list)


class ImprovementSuggestion(BaseModel):
    suggestion: str
    reason: str


class JobMatchResult(BaseModel):
    match_percentage: int = Field(ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    improvement_suggestions: list[ImprovementSuggestion] = Field(default_factory=list)
