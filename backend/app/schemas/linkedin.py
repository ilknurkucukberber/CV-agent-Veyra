from app.agents.linkedin_schema import HEADLINE_MAX_LENGTH
from app.schemas.base import APISchema


class ExperienceDescriptionSchema(APISchema):
    role: str
    linkedin_version: str


class ChecklistItemSchema(APISchema):
    item: str
    present: bool | None


class LinkedInOptimizeResponse(APISchema):
    headline_options: list[str]
    about_section: str
    experience_descriptions: list[ExperienceDescriptionSchema]
    suggested_skills: list[str]
    profile_completeness_checklist: list[ChecklistItemSchema]
    headline_max_length: int = HEADLINE_MAX_LENGTH
