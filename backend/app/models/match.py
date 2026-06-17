"""
Match SQLAlchemy Model.

Represents a 1v1 coding battle between two players.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MatchStatus(str, PyEnum):
    """Possible states of a match."""
    PENDING = "pending"         # Matched, waiting to start
    ACTIVE = "active"           # Battle is live
    COMPLETED = "completed"     # One player solved / time ran out
    CANCELLED = "cancelled"     # A player left or disconnected


class Match(Base):
    """
    A 1v1 coding battle session.

    Fields:
        id          - Auto-increment primary key
        player1_id  - FK to users.id (the user who initiated / was first in queue)
        player2_id  - FK to users.id (the matched opponent)
        problem_id  - FK to problems.id (the DSA problem being solved)
        status      - Current state of the match
        winner_id   - FK to users.id (null until match ends)
        started_at  - When the battle began (after countdown)
        ended_at    - When the battle finished
        created_at  - When the match record was created (matchmaking time)
    """

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player1_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player2_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
    )
    winner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.PENDING, nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    player1 = relationship("User", foreign_keys=[player1_id], back_populates="matches_as_player1")
    player2 = relationship("User", foreign_keys=[player2_id], back_populates="matches_as_player2")
    problem = relationship("Problem", back_populates="matches")
    submissions = relationship("Submission", back_populates="match")

    def __repr__(self) -> str:
        return f"<Match id={self.id} status={self.status} p1={self.player1_id} p2={self.player2_id}>"
