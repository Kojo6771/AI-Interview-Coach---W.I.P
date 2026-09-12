# InterviewSession represents a single interview practice session created by a user.
# It links the user and the CV used, along with the interview configuration and progress status.
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import relationship

from app.database import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    cv_id = Column(
        Integer,
        ForeignKey("cv_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    target_role = Column(
        String(255),
        nullable=False
    )

    job_description = Column(
        Text,
        nullable=True
    )

    interview_type = Column(
        String(50),
        nullable=False
    )

    difficulty = Column(
        String(50),
        nullable=False
    )

    status = Column(
        String(50),
        default="created",
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    answers = relationship(
        "Answer",
        back_populates="interview",
        cascade="all, delete-orphan"
    )
