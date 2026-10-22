# Pydantic schemas for creating and returning interview sessions.
from datetime import datetime, timezone
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

    @field_validator("completed_at")
    @classmethod
    def normalize_completed_at(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class InterviewDetailResponse(InterviewResponse):
    pass


class InterviewResultsResponse(BaseModel):
    interview_id: int
    status: str
    total_questions: int
    submitted_answers: int
    evaluated_answers: int
    average_score: Optional[float] = None
    remaining_questions: int
    ready_for_completion: bool
