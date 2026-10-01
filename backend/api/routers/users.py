from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from database import Database, get_database
from dependencies import get_current_user
from models.user import UserProfile, UserProfileResponse, UserProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_me(user: UserProfile = Depends(get_current_user)) -> UserProfileResponse:
    return UserProfileResponse(user=user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(update: UserProfileUpdate, user: UserProfile = Depends(get_current_user), database: Database = Depends(get_database)) -> UserProfileResponse:
    updated = await database.update_user(user.id, update)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserProfileResponse(user=updated)
