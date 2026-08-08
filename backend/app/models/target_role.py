# TargetRole contains the catalog of job roles used to define interview goals.
# Each interview can point to a target role such as software engineer or product manager.
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text
)

from app.database import Base


class TargetRole(Base):

    __tablename__ = "target_roles"

    id = Column(
        Integer,
        primary_key=True
    )

    name = Column(
        String(255),
        unique=True,
        nullable=False
    )

    description = Column(
        Text
    )