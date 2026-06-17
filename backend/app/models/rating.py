"""
Rating SQLAlchemy Model.

Tracks ELO-style rating history for each player.
Each row is a snapshot after a match (rating changed by delta).
"""

from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Rating(Base):
    """
    Rating history record for a user.

    Instead of storing just the current rating on the User model,
    we also keep a history table so players can see their progression.

    Fields:
        id          - Auto-increment primary key
        user_id     - FK to users.id (one-to-one for current, one-to-many for history)
        match_id    - FK to matches.id (which match caused this change)
        old_rating  - Rating before this match
        new_rating  - Rating after this match
        delta       - Change (+/- points)
        created_at  - When this rating change happened
    """

    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True
    )

    old_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    new_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)  # +25, -15, etc.

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user = relationship("User", back_populates="rating_record")

    def __repr__(self) -> str:
        return f"<Rating user={self.user_id} {self.old_rating}→{self.new_rating} ({self.delta:+d})>"
