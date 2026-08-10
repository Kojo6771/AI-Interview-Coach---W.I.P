# User is the main authentication and account record for the application.
# It stores the login identity, password hash, access role, and lifecycle flags.
from sqlalchemy import (Column, Integer, String, Boolean, DateTime)


from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    # The live PostgreSQL schema stores the auth digest under hashed_password.
    hashed_password = Column(
        "hashed_password",
        String(255),
        nullable=False
    )

    # role = Column(
    #     String(50),
    #     default="user",
    #     nullable=False
    # )

    # is_active = Column(
    #     Boolean,
    #     default=True,
    #     nullable=False
    # )

    # created_at = Column(
    #     DateTime(timezone=True),
    #     server_default=func.now()
    # )

    # updated_at = Column(
    #     DateTime(timezone=True),
    #     server_default=func.now(),
    #     onupdate=func.now()
    # )