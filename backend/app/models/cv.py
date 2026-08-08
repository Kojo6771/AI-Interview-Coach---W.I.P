# CVDocument stores an uploaded resume or curriculum vitae for a user.
# The extracted_text field keeps parsed CV content used for interview generation.
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)
from sqlalchemy.sql import func

from app.database import Base


class CVDocument(Base):

    __tablename__ = "cv_documents"

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    filename = Column(
        String(255),
        nullable=False
    )

    file_path = Column(
        String(500),
        nullable=False
    )

    extracted_text = Column(
        Text
    )

    uploaded_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )