"""
Submission SQLAlchemy Model.

Records every code submission made by a player during a match.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SubmissionStatus(str, PyEnum):
    """Result of a submission after running test cases."""
    PENDING = "pending"             # Just submitted, awaiting judge
    RUNNING = "running"             # Currently being evaluated
    ACCEPTED = "accepted"           # All test cases passed ✅
    WRONG_ANSWER = "wrong_answer"   # Output doesn't match expected
    TIME_LIMIT = "time_limit"       # Exceeded time limit
    MEMORY_LIMIT = "memory_limit"   # Exceeded memory limit
    RUNTIME_ERROR = "runtime_error" # Code threw an exception
    COMPILE_ERROR = "compile_error" # Code failed to compile


class Submission(Base):
    """
    A single code submission from a player.

    Fields:
        id              - Auto-increment primary key
        user_id         - FK to users.id
        match_id        - FK to matches.id (null if practice submission)
        problem_id      - FK to problems.id
        language        - Programming language (python, java, cpp, etc.)
        code            - The submitted source code
        status          - Result of the submission
        runtime_ms      - Execution time in milliseconds
        memory_kb       - Memory used in kilobytes
        created_at      - Submission timestamp
    """

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )

    language: Mapped[str] = mapped_column(String(30), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.PENDING, nullable=False
    )

    runtime_ms: Mapped[float] = mapped_column(Float, nullable=True)
    memory_kb: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user = relationship("User", back_populates="submissions")
    match = relationship("Match", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")

    def __repr__(self) -> str:
        return f"<Submission id={self.id} user={self.user_id} status={self.status}>"
