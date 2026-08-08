# Question represents an individual interview prompt that belongs to a single interview.
# It carries the question body, generation attributes, and ordering within that interview.
from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    ForeignKey
)

from app.database import Base


class Question(Base):

    __tablename__ = "questions"

    id = Column(
        Integer,
        primary_key=True
    )

    interview_id = Column(
        Integer,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False
    )

    question_text = Column(
        Text,
        nullable=False
    )

    question_type = Column(
        String(50),
        nullable=False
    )

    difficulty = Column(
        String(50)
    )

    question_order = Column(
        Integer,
        nullable=False
    )

    generated_by = Column(
        String(50),
        default="ai"
    )