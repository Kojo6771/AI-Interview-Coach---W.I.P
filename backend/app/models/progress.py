# Progress stores learner performance aggregates by user.
# The table summarizes completed interview counts and average scoring dimensions over time.
from sqlalchemy import (
    Column,
    Integer,
    Float,
    DateTime,
    ForeignKey
)
from sqlalchemy.sql import func

from app.database import Base


class Progress(Base):

    __tablename__ = "progress"

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    interviews_completed = Column(
        Integer,
        default=0
    )

    average_score = Column(
        Float,
        default=0
    )

    average_communication_score = Column(
        Float,
        default=0
    )

    average_technical_score = Column(
        Float,
        default=0
    )

    average_clarity_score = Column(
        Float,
        default=0
    )

    average_confidence_score = Column(
        Float,
        default=0
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )