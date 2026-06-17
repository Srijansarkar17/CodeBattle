"""
Contest SQLAlchemy Model.

A Contest is a larger competitive event (tournament) that can contain
multiple matches and players competing for ranking.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, DateTime, Enum, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContestStatus(str, PyEnum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class Contest(Base):
    """
    An organized contest/tournament event.

    Fields:
        id              - Auto-increment primary key
        title           - Display name of the contest
        description     - Full description (Markdown)
        status          - Current contest status
        max_participants- Maximum number of entrants allowed
        start_time      - When the contest begins
        end_time        - When the contest ends
        problem_ids     - JSON list of problem IDs in this contest
        created_at      - When the contest was created
    """

    __tablename__ = "contests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ContestStatus] = mapped_column(
        Enum(ContestStatus), default=ContestStatus.UPCOMING, nullable=False
    )
    max_participants: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    problem_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Contest id={self.id} title={self.title!r} status={self.status}>"
