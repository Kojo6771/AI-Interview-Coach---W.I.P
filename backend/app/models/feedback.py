# Feedback records the automated evaluation for a single answer submission.
# It stores the scored rubric dimensions and narrative coaching content.
from sqlalchemy import (
    Column,
    Integer,
    Text,
    Float,
    ForeignKey,
    DateTime
)
from sqlalchemy.sql import func

from app.database import Base


class Feedback(Base):

    __tablename__ = "feedback"

    id = Column(
        Integer,
        primary_key=True
    )

    answer_id = Column(
        Integer,
        ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    overall_score = Column(
        Float,
        nullable=False
    )

    communication_score = Column(
        Float
    )

    technical_score = Column(
        Float
    )

    clarity_score = Column(
        Float
    )

    confidence_score = Column(
        Float
    )

    strengths = Column(
        Text
    )

    weaknesses = Column(
        Text
    )

    suggestions = Column(
        Text
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )