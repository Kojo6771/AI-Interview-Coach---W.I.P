# Answer stores the candidate's written response to a single interview question.
# app/models/answer.py
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    String
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Answer(Base):

    __tablename__ = "answers"

    id = Column(
        Integer,
        primary_key=True
    )

    # unique=True enforces one answer per question at the database level
    question_id = Column(
        Integer,
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # denormalized so answers for an interview can be queried without a join
    interview_id = Column(
        Integer,
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    answer_text = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Tracks the revision number of the answer, incremented with each update
    answer_revision = Column(
        Integer,
        nullable=False,
        default=1
    )

    evaluation_token = Column(
        String(36),
        nullable=True
    )

    question = relationship("InterviewQuestion", back_populates="answer")
    interview = relationship("InterviewSession", back_populates="answers")