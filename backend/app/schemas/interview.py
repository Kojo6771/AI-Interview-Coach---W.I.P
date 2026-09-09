# Pydantic schemas for creating and returning interview sessions.
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

ALLOWED_INTERVIEW_TYPES = {"behavioural", "technical", "mixed"}
ALLOWED_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


class InterviewCreate(BaseModel):
    cv_id: int
    target_role: str
    job_description: Optional[str] = None
    interview_type: str
    difficulty: str

    @field_validator("interview_type")
    @classmethod
    def validate_interview_type(cls, value: str) -> str:
        if value not in ALLOWED_INTERVIEW_TYPES:
            raise ValueError(
                f"interview_type must be one of {sorted(ALLOWED_INTERVIEW_TYPES)}"
            )
        return value

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        if value not in ALLOWED_DIFFICULTIES:
            raise ValueError(
                f"difficulty must be one of {sorted(ALLOWED_DIFFICULTIES)}"
            )
        return value


class InterviewResponse(BaseModel):
    id: int
    user_id: int
    cv_id: int
    target_role: str
    job_description: Optional[str] = None
    interview_type: str
    difficulty: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InterviewDetailResponse(InterviewResponse):
    pass
