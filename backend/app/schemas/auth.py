"""
Authentication Pydantic Schemas.

These are the request/response bodies for auth endpoints.
Pydantic validates all incoming data automatically.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class RegisterRequest(BaseModel):
    """Body for POST /api/v1/auth/register"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique display name (3-50 chars, alphanumeric + underscore)",
        examples=["coder_pro"],
    )
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars)",
        examples=["Str0ngP@ss!"],
    )

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Username can only contain letters, numbers, and underscores."""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username may only contain letters, numbers, and underscores"
            )
        return v.lower()


class LoginRequest(BaseModel):
    """Body for POST /api/v1/auth/login"""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class TokenResponse(BaseModel):
    """Response returned after successful login or register."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Internal model: decoded JWT payload."""

    user_id: str
