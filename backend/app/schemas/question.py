# Pydantic schemas for creating and returning interview questions.
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

ALLOWED_QUESTION_TYPES = {"behavioural", "technical", "situational"}
ALLOWED_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


class QuestionCreate(BaseModel):
    question_text: str
    question_type: str
    difficulty: str
    order_number: int

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, value: str) -> str:
        if value not in ALLOWED_QUESTION_TYPES:
            raise ValueError(
                f"question_type must be one of {sorted(ALLOWED_QUESTION_TYPES)}"
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


class QuestionResponse(BaseModel):
    id: int
    interview_id: int
    question_text: str
    question_type: str
    difficulty: str
    order_number: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
