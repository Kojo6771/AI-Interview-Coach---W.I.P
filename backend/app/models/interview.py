# Interview represents a concrete interview session created for a user.
# It links the user, selected role, optional CV, and final interview status and score.
# app/models/interview.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey
)
from sqlalchemy.sql import func

from app.database import Base


class Interview(Base):

    __tablename__ = "interviews"

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    target_role_id = Column(
        Integer,
        ForeignKey("target_roles.id"),
        nullable=False
    )

    cv_id = Column(
        Integer,
        ForeignKey("cv_documents.id", ondelete="SET NULL"),
        nullable=True
    )

    interview_type = Column(
        String(50),
        nullable=False
    )

    status = Column(
        String(50),
        default="in_progress",
        nullable=False
    )

    overall_score = Column(
        Float
    )

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    completed_at = Column(
        DateTime(timezone=True)
    )