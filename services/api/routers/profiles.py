"""Authenticated endpoints for a user's own contact profile."""

from fastapi import APIRouter, Depends, HTTPException, status

from services.api.auth_dependencies import get_current_user
from services.api.auth_models import ProfileResponse, ProfileUpdate, UserRecord
from services.api.user_service import ProfileNotFoundError, get_profile_by_user_id, update_profile

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def _raise_profile_not_found() -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found") from None


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user: UserRecord = Depends(get_current_user)) -> ProfileResponse:
    try:
        return get_profile_by_user_id(current_user.id)
    except ProfileNotFoundError:
        _raise_profile_not_found()


@router.put("/me", response_model=ProfileResponse)
def put_my_profile(
    update: ProfileUpdate,
    current_user: UserRecord = Depends(get_current_user),
) -> ProfileResponse:
    try:
        return update_profile(current_user.id, update)
    except ProfileNotFoundError:
        _raise_profile_not_found()
