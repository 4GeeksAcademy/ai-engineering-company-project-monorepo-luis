"""Public registration and owner/admin-only credential management."""

from fastapi import APIRouter, Depends, HTTPException, status

from services.api.auth_dependencies import get_current_user
from services.api.auth_models import (
    UserCreate,
    UserRecord,
    UserRegistration,
    UserResponse,
    UserRole,
    UserUpdate,
)
from services.api.user_service import (
    DuplicateEmailError,
    ProfileNotFoundError,
    RegistrationRoleError,
    UserNotFoundError,
    create_user,
    delete_user,
    get_user_by_id,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["Users"])


def _is_admin(user: UserRecord) -> bool:
    return user.role == UserRole.ADMIN


def _authorize_owner_or_admin(target_user_id: int, current_user: UserRecord) -> None:
    if current_user.id != target_user_id and not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def _raise_user_not_found() -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from None


def _raise_duplicate_email() -> None:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from None


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(registration: UserRegistration) -> UserResponse:
    try:
        user = create_user(
            UserCreate(
                email=registration.email,
                password=registration.password,
                name=registration.name,
                phone=registration.phone,
                address=registration.address,
            )
        )
    except DuplicateEmailError:
        _raise_duplicate_email()
    except RegistrationRoleError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid registration role") from None
    return user


@router.get("", response_model=list[UserResponse])
def get_users(current_user: UserRecord = Depends(get_current_user)) -> list[UserResponse]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return list_users()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: UserRecord = Depends(get_current_user)) -> UserResponse:
    _authorize_owner_or_admin(user_id, current_user)
    try:
        return get_user_by_id(user_id)
    except UserNotFoundError:
        _raise_user_not_found()


@router.put("/{user_id}", response_model=UserResponse)
def put_user(
    user_id: int,
    update: UserUpdate,
    current_user: UserRecord = Depends(get_current_user),
) -> UserResponse:
    _authorize_owner_or_admin(user_id, current_user)
    privileged_fields = {"role", "is_active"} & update.model_fields_set
    if privileged_fields and not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an admin can change role or account status")
    try:
        return update_user(user_id, update)
    except UserNotFoundError:
        _raise_user_not_found()
    except DuplicateEmailError:
        _raise_duplicate_email()


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def remove_user(user_id: int, current_user: UserRecord = Depends(get_current_user)) -> dict[str, int | bool]:
    _authorize_owner_or_admin(user_id, current_user)
    try:
        delete_user(user_id)
    except UserNotFoundError:
        _raise_user_not_found()
    except ProfileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found") from None
    return {"id": user_id, "deleted": True}
