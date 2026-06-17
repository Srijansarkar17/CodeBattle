"""
User SQLAlchemy Model.

Represents a registered player on the platform.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """
    Core user entity.

    Fields:
        id              - Auto-increment primary key
        username        - Unique display name (shown in battle arena)
        email           - Unique email for login
        hashed_password - bcrypt-hashed password (never store plain text!)
        rating          - ELO-style rating, starts at 1200
        is_active       - False = banned/deactivated account
        created_at      - Account creation timestamp
        updated_at      - Last profile update timestamp
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # One user can participate in many matches (as player1 or player2)
    matches_as_player1 = relationship(
        "Match", foreign_keys="Match.player1_id", back_populates="player1"
    )
    matches_as_player2 = relationship(
        "Match", foreign_keys="Match.player2_id", back_populates="player2"
    )

    # One user has one rating record
    rating_record = relationship("Rating", back_populates="user", uselist=False)

    # One user has many submissions
    submissions = relationship("Submission", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} rating={self.rating}>"
