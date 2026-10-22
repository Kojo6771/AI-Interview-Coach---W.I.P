# Feedback records the AI evaluation of a single submitted answer.
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    Text,
    JSON,
    ForeignKey,
    DateTime
)

from app.database import Base


class Feedback(Base):

    __tablename__ = "feedback"

    id = Column(
        Integer,
        primary_key=True
    )

    # one active evaluation per answer
    answer_id = Column(
        Integer,
        ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    score = Column(
        Integer,
        nullable=False
    )

    # list[str], not a delimited/plain string
    strengths = Column(
        JSON,
        nullable=False
    )

    improvements = Column(
        JSON,
        nullable=False
    )

    feedback_text = Column(
        Text,
        nullable=False
    )

    improved_answer = Column(
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
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )