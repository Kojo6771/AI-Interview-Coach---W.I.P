from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey
)

from app.database import Base


class UserProfile(Base):

    __tablename__ = "user_profiles"

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    first_name = Column(
        String(100)
    )

    last_name = Column(
        String(100)
    )

    university = Column(
        String(255)
    )

    degree = Column(
        String(255)
    )

    bio = Column(
        Text
    )

    profile_picture = Column(
        String(500)
    )