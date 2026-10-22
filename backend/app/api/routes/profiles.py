from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Profile
from app.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _get_profile_or_404(db: DbSession, user_id: int) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil bulunamadı",
        )
    return profile


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(payload: ProfileCreate, current_user: CurrentUser, db: DbSession) -> Profile:
    existing = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu kullanıcı için profil zaten mevcut",
        )

    profile = Profile(user_id=current_user.id, **payload.model_dump(exclude_unset=True))
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user: CurrentUser, db: DbSession) -> Profile:
    return _get_profile_or_404(db, current_user.id)


@router.patch("/me", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdate, current_user: CurrentUser, db: DbSession
) -> Profile:
    profile = _get_profile_or_404(db, current_user.id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile
