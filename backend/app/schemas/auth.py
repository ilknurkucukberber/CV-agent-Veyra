from pydantic import EmailStr, Field

from app.schemas.base import APISchema


class UserLogin(APISchema):
    email: EmailStr
    password: str


class Token(APISchema):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(APISchema):
    sub: str
    exp: int


class PasswordResetRequest(APISchema):
    email: EmailStr


class PasswordResetConfirm(APISchema):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class EmailVerificationConfirm(APISchema):
    token: str


class ResendVerificationRequest(APISchema):
    email: EmailStr
