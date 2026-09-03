# CVDocument stores an uploaded resume or curriculum vitae for a user.
# The extracted_text field keeps parsed CV content used for interview generation.
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from app.database import Base

# CVDocument is a SQLAlchemy model representing a CV document in the database.
class CVDocument(Base):
    __tablename__ = "cv_documents"

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

    filename = Column(
        String(255),
        nullable=False
    )

    file_type = Column(
        String(10),
        nullable=False
    )

    file_path = Column(
        String(500),
        nullable=True
    )

    extracted_text = Column(
        Text,
        nullable=False
    )

    uploaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )