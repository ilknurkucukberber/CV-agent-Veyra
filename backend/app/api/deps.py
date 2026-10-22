from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Geçersiz veya eksik kimlik bilgisi",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise CREDENTIALS_EXC

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise CREDENTIALS_EXC

    try:
        user_id = int(payload.get("sub", ""))
    except ValueError:
        raise CREDENTIALS_EXC

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise CREDENTIALS_EXC
    return user

def get_language(request: Request) -> str:
    lang = request.headers.get("Accept-Language", "tr")
    return lang.split(",")[0].split("-")[0].lower()


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
Language = Annotated[str, Depends(get_language)]
