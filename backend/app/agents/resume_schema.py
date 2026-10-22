from pydantic import BaseModel, Field

# Not: nullable alanlara `= None`, liste alanlara `= Field(default_factory=list)`
# vermek zorunludur. Aksi halde, model (özellikle Groq/Llama) bir CV'de
# karşılığı olmayan bir alanı (ör. teknoloji listesi belirtilmemiş bir proje)
# JSON'da tamamen ATLADIĞINDA — null göndermek yerine — Pydantic bunu "eksik
# alan" hatası sayıp TÜM parse işlemini çökertiyordu (bkz. gerçek bir CV ile
# tekrarlanan `projects.N.technologies: Field required` hatası).


class PersonalInfo(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class EducationEntry(BaseModel):
    school: str
    department: str
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None


class ExperienceEntry(BaseModel):
    company: str
    role: str
    start_date: str | None = None
    end_date: str | None = None
    description: str


class ProjectEntry(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    link: str | None = None


class LanguageEntry(BaseModel):
    language: str
    level: str | None = None


class ParsedResume(BaseModel):
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
