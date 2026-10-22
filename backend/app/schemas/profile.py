from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import WorkModePreference
from app.schemas.base import APISchema, ORMSchema


class ProfileBase(APISchema):
    education_level: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=255)
    university: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1950, le=2035)
    work_experience: list[Any] | None = None
    internship_experience: list[Any] | None = None
    technical_skills: list[Any] | None = None
    certificates: list[Any] | None = None
    projects: list[Any] | None = None
    english_level: str | None = Field(default=None, max_length=20)
    target_city: str | None = Field(default=None, max_length=255)
    work_mode_preference: WorkModePreference | None = None
    career_goal: str | None = Field(default=None, max_length=5000)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ORMSchema, ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
