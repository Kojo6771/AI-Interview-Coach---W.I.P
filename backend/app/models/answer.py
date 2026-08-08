# Answer stores the candidate's submitted response for a single interview question.
# Audio capture and text answer content are persisted here for evaluation.
# app/models/answer.py

from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    DateTime,
    ForeignKey
)
from sqlalchemy.sql import func

from app.database import Base


class Answer(Base):

    __tablename__ = "answers"

    id = Column(
        Integer,
        primary_key=True
    )

    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False
    )

    answer_text = Column(
        Text
    )

    audio_path = Column(
        String(500)
    )

    submitted_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )