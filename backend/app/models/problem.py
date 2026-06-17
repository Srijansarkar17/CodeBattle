"""
Problem SQLAlchemy Model.

Represents a DSA (Data Structures & Algorithms) coding problem.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, Text, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Difficulty(str, PyEnum):
    """Problem difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Problem(Base):
    """
    A coding problem that players solve during a match.

    Fields:
        id          - Auto-increment primary key
        title       - Short display name (e.g., "Two Sum")
        slug        - URL-friendly identifier (e.g., "two-sum")
        description - Full problem statement (Markdown supported)
        difficulty  - easy / medium / hard
        tags        - JSON array of topic tags (e.g., ["array", "hash-map"])
        examples    - JSON array of example input/output pairs
        constraints - Text describing input constraints
        starter_code- JSON mapping language → starter code template
        created_at  - When the problem was added
    """

    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty), default=Difficulty.MEDIUM, nullable=False
    )
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    examples: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    constraints: Mapped[str] = mapped_column(Text, nullable=True)
    starter_code: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    matches = relationship("Match", back_populates="problem")
    submissions = relationship("Submission", back_populates="problem")

    def __repr__(self) -> str:
        return f"<Problem id={self.id} slug={self.slug!r} difficulty={self.difficulty}>"
