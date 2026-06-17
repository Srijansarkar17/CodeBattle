"""
User Profile API Endpoints.

GET  /api/v1/users/me           — Get own full profile (private)
PATCH /api/v1/users/me          — Update own profile
GET  /api/v1/users/{username}   — Get another user's public profile
GET  /api/v1/users/leaderboard  — Top players by rating
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.user import UserPublicProfile, UserPrivateProfile, UserUpdateRequest

router = APIRouter()


@router.get(
    "/me",
    response_model=UserPrivateProfile,
    summary="Get my profile (requires authentication)",
)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserPrivateProfile:
    """
    Returns the full profile of the currently authenticated user,
    including email and account status.
    """
    return UserPrivateProfile.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserPrivateProfile,
    summary="Update my profile",
)
async def update_my_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserPrivateProfile:
    """
    Updates the current user's username or email.
    Only provided fields are changed (partial update).
    """
    if payload.username is not None:
        # Check new username not taken
        existing = await db.execute(
            select(User).where(User.username == payload.username)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken.",
            )
        current_user.username = payload.username

    if payload.email is not None:
        existing = await db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use.",
            )
        current_user.email = str(payload.email)

    await db.flush()
    await db.refresh(current_user)
    return UserPrivateProfile.model_validate(current_user)


@router.get(
    "/leaderboard",
    response_model=List[UserPublicProfile],
    summary="Get top-rated players",
)
async def get_leaderboard(
    limit: int = Query(default=50, ge=1, le=100, description="Number of players to return"),
    db: AsyncSession = Depends(get_db),
) -> List[UserPublicProfile]:
    """
    Returns the top N players sorted by rating (highest first).
    Public endpoint — no authentication required.
    """
    result = await db.execute(
        select(User)
        .where(User.is_active == True)
        .order_by(desc(User.rating))
        .limit(limit)
    )
    users = result.scalars().all()
    return [UserPublicProfile.model_validate(u) for u in users]


@router.get(
    "/{username}",
    response_model=UserPublicProfile,
    summary="Get a player's public profile",
)
async def get_user_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> UserPublicProfile:
    """
    Returns the public profile of any active user by username.
    """
    result = await db.execute(
        select(User).where(User.username == username, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found.",
        )
    return UserPublicProfile.model_validate(user)
