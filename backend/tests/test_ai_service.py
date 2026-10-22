import json
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError
from pydantic import ValidationError

from app.schemas.feedback import AIEvaluationResult
from app.services import ai_service


def _evaluation(**overrides):
    result = {
        "score": 82,
        "strengths": ["Clear explanation"],
        "improvements": ["Add a measurable outcome"],
        "feedback": "The response is relevant and easy to follow.",
        "improved_answer": "I explained the design and the trade-offs."
    }
    result.update(overrides)
    return result


def _completion(content):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=content))
        ]
    )


class _Completions:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        return response


def _client(completions):
    return SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )


@pytest.fixture
def configured_service(monkeypatch):
    monkeypatch.setattr(ai_service, "OpenAI_Api_Key", "test-key")
    monkeypatch.setattr(ai_service, "OpenAI_Max_Retries", 0)


def test_successful_evaluation_uses_structured_schema_and_rubric(
    configured_service, monkeypatch
):
    completion = _Completions([_completion(json.dumps(_evaluation()))])
    client_kwargs = {}

    def fake_openai(**kwargs):
        client_kwargs.update(kwargs)
        return _client(completion)

    monkeypatch.setattr(ai_service, "OpenAI", fake_openai)

    result = ai_service.evaluate_interview_answer(
        "Describe a challenge.",
        "I explained the design and trade-offs.",
        "behavioural",
        "Engineer",
        "intermediate",
    )

    assert 0 <= result["score"] <= 100
    assert result["feedback_text"]
    assert result["improved_answer"]
    assert completion.calls[0]["response_format"]["type"] == "json_schema"
    assert client_kwargs["timeout"] > 0
    assert client_kwargs["max_retries"] == 0
    system_prompt = completion.calls[0]["messages"][0]["content"]
    assert "25%" in system_prompt
    assert "20%" in system_prompt
    assert "10%" in system_prompt
    assert "Never add achievements" in system_prompt
    assert "behavioural question" in completion.calls[0]["messages"][1]["content"]


@pytest.mark.parametrize("score", [-1, 101])
def test_score_outside_range_is_rejected(score):
    with pytest.raises(ValidationError):
        AIEvaluationResult.model_validate(_evaluation(score=score))


@pytest.mark.parametrize(
    "payload",
    [
        {"score": 80},
        _evaluation(strengths=[]),
        _evaluation(improvements=[]),
        _evaluation(feedback="  "),
        _evaluation(improved_answer=" "),
        _evaluation(score=81.5),
        _evaluation(unexpected="extra"),
    ],
)
def test_invalid_or_missing_feedback_fields_are_rejected(payload):
    with pytest.raises(ValidationError):
        AIEvaluationResult.model_validate(payload)


def test_missing_api_key_is_reported_without_provider_call(monkeypatch):
    monkeypatch.setattr(ai_service, "OpenAI_Api_Key", None)

    with pytest.raises(ai_service.AIServiceError, match="not configured"):
        ai_service.evaluate_interview_answer(
            "Question", "Answer", "technical", "Engineer", "beginner"
        )


@pytest.mark.parametrize(
    "error",
    [
        APITimeoutError(request=httpx.Request("POST", "https://api.openai.com")),
        RateLimitError(
            "rate limited",
            response=httpx.Response(
                429, request=httpx.Request("POST", "https://api.openai.com")
            ),
            body={"error": "rate limited"},
        ),
        APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com")
        ),
    ],
)
def test_provider_timeout_rate_limit_and_connection_errors_are_normalized(
    configured_service, monkeypatch, error
):
    completion = _Completions([error])
    monkeypatch.setattr(ai_service, "OpenAI", lambda **kwargs: _client(completion))

    with pytest.raises(ai_service.AIServiceError):
        ai_service.evaluate_interview_answer(
            "Question", "Answer", "technical", "Engineer", "beginner"
        )


def test_transient_provider_error_is_retried_only_within_bound(
    configured_service, monkeypatch
):
    monkeypatch.setattr(ai_service, "OpenAI_Max_Retries", 1)
    monkeypatch.setattr(ai_service.time, "sleep", lambda _: None)
    completion = _Completions(
        [
            APIConnectionError(
                request=httpx.Request("POST", "https://api.openai.com")
            ),
            _completion(json.dumps(_evaluation())),
        ]
    )
    monkeypatch.setattr(ai_service, "OpenAI", lambda **kwargs: _client(completion))

    ai_service.evaluate_interview_answer(
        "Question", "Answer", "technical", "Engineer", "beginner"
    )

    assert len(completion.calls) == 2


@pytest.mark.parametrize("content", ["{not json", "", None])
def test_malformed_model_response_is_rejected(configured_service, monkeypatch, content):
    completion = _Completions([_completion(content)])
    monkeypatch.setattr(ai_service, "OpenAI", lambda **kwargs: _client(completion))

    with pytest.raises(ai_service.AIResponseError):
        ai_service.evaluate_interview_answer(
            "Question", "Answer", "technical", "Engineer", "beginner"
        )


def test_improved_answer_must_be_nonblank_and_cannot_add_unknown_fields():
    with pytest.raises(ValidationError):
        AIEvaluationResult.model_validate(
            _evaluation(improved_answer="  ")
        )
