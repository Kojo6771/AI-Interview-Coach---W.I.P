# Pydantic schemas for AI answer evaluation and stored feedback.
from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
)

from app.schemas.answer import AnswerResponse
from app.schemas.question import QuestionResponse


def _validate_string_list(value: list[str]) -> list[str]:
    cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]

    if not cleaned:
        raise ValueError("list must contain at least one non-blank string")

    return cleaned


# Validates the raw AI JSON response before anything is persisted
class AIEvaluationResult(BaseModel):
    score: Annotated[StrictInt, Field(ge=0, le=100)]
    strengths: list[StrictStr] = Field(min_length=1)
    improvements: list[StrictStr] = Field(min_length=1)
    feedback: StrictStr = Field(min_length=1)
    improved_answer: StrictStr = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("strengths", "improvements")
    @classmethod
    def validate_string_lists(cls, value: list[str]) -> list[str]:
        return _validate_string_list(value)

    @field_validator("feedback", "improved_answer")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        stripped = value.strip()

        if not stripped:
            raise ValueError("value cannot be blank")

        return stripped


class FeedbackResponse(BaseModel):
    id: int
    answer_id: int
    score: int
    strengths: list[str]
    improvements: list[str]
    feedback_text: str
    improved_answer: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# combines the question, answer, and evaluation for the GET feedback endpoint
class QuestionAnswerFeedbackResponse(BaseModel):
    question: QuestionResponse
    answer: AnswerResponse
    evaluation: FeedbackResponse

    model_config = ConfigDict(from_attributes=True)
