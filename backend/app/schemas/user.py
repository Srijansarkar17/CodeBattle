"""
User Pydantic Schemas.

Input validation and output serialization for user-related endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserPublicProfile(BaseModel):
    """
    Public view of a user — safe to expose to anyone.
    Does NOT include email or hashed_password.
    """

    id: int
    username: str
    rating: int
    created_at: datetime

    model_config = {"from_attributes": True}  # Allows creating from ORM objects


class UserPrivateProfile(BaseModel):
    """
    Private view of the current user — includes email.
    Only returned when the user requests their own profile.
    """

    id: int
    username: str
    email: EmailStr
    rating: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Body for PATCH /api/v1/users/me — update own profile."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
