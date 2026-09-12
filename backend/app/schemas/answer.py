# Pydantic schemas for submitting, updating, and returning interview answers.
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_ANSWER_LENGTH = 5000

# Helper function to validate answer text
def _validate_answer_text(value: str) -> str:
    stripped = value.strip()

    if not stripped:
        raise ValueError("answer_text cannot be blank")

    return stripped

# Schema for creating a new answer
class AnswerCreate(BaseModel):
    answer_text: str = Field(min_length=1, max_length=MAX_ANSWER_LENGTH)

    @field_validator("answer_text")
    @classmethod
    def validate_answer_text(cls, value: str) -> str:
        return _validate_answer_text(value)

# Schema for updating an existing answer
class AnswerUpdate(BaseModel):
    answer_text: str = Field(min_length=1, max_length=MAX_ANSWER_LENGTH)

    @field_validator("answer_text")
    @classmethod
    def validate_answer_text(cls, value: str) -> str:
        return _validate_answer_text(value)


class AnswerResponse(BaseModel):
    id: int
    question_id: int
    interview_id: int
    answer_text: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# combines an answer with its question for the "all answers in an interview" endpoint
class InterviewAnswerResponse(BaseModel):
    id: int
    question_id: int
    question_order: int
    question_text: str
    answer_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
