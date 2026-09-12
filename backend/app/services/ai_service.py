# Generates personalised interview questions from a candidate's CV and interview config.
# Keeps all AI provider details out of the route layer.
import json

from openai import OpenAI

from app.config import OpenAI_Api_Key
from app.schemas.question import ALLOWED_QUESTION_TYPES

DEFAULT_MODEL = "gpt-4o"


class AIServiceError(Exception):
    """Raised when the AI provider is not configured or cannot be reached."""


class AIResponseError(Exception):
    """Raised when the AI provider returns a response we cannot use."""


def _build_prompt(
    cv_text: str,
    target_role: str,
    job_description: str | None,
    interview_type: str,
    difficulty: str,
    number_of_questions: int
) -> str:
    # question_type values are constrained to ALLOWED_QUESTION_TYPES so AI output stays DB-valid
    return (
        "Candidate CV:\n"
        f"{cv_text}\n\n"
        f"Target role: {target_role}\n"
        f"Job description: {job_description or 'Not provided'}\n"
        f"Interview type: {interview_type}\n"
        f"Difficulty: {difficulty}\n\n"
        f"Generate exactly {number_of_questions} interview questions for this candidate. "
        "Personalise questions using specific details from the CV and target role wherever "
        "possible (e.g. mention a real project, technology, or responsibility from the CV). "
        "Never invent experience that is not present in the CV. "
        "Use a balanced mixture of question types drawn only from: "
        f"{sorted(ALLOWED_QUESTION_TYPES)}.\n\n"
        "Return your answer as JSON matching this exact shape, with no extra text:\n"
        '{"questions": [{"question_text": "...", "question_type": "behavioural"}]}'
    )


def generate_interview_questions(
    cv_text: str,
    target_role: str,
    job_description: str | None,
    interview_type: str,
    difficulty: str,
    number_of_questions: int = 5
) -> list[dict]:
    # fail fast so the route can return a clean error instead of an SDK exception
    if not OpenAI_Api_Key:
        raise AIServiceError("OpenAI API key is not configured")

    prompt = _build_prompt(
        cv_text,
        target_role,
        job_description,
        interview_type,
        difficulty,
        number_of_questions
    )

    # any network/auth/rate-limit failure from the SDK is treated the same way
    try:
        client = OpenAI(api_key=OpenAI_Api_Key)

        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an experienced technical interviewer who writes "
                        "personalised, fair interview questions and always responds "
                        "with valid JSON only."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        raw_content = completion.choices[0].message.content

    except Exception as e:
        print("AI SERVICE ERROR:", repr(e))

        raise AIServiceError("Failed to reach the AI provider") from e

    # response_format=json_object guarantees valid JSON syntax, not our expected shape
    try:
        data = json.loads(raw_content)

    except json.JSONDecodeError as e:
        print("AI RESPONSE ERROR: invalid JSON:", repr(e))

        raise AIResponseError("AI provider returned invalid JSON") from e

    # defend against the model omitting or mistyping the "questions" key
    questions = data.get("questions") if isinstance(data, dict) else None

    if not isinstance(questions, list) or not questions:
        raise AIResponseError("AI provider response did not contain any questions")

    cleaned_questions = []

    # validate every item before any of it reaches the database layer
    for item in questions:
        if not isinstance(item, dict):
            raise AIResponseError("AI provider returned a malformed question")

        question_text = item.get("question_text")
        question_type = item.get("question_type")

        if not isinstance(question_text, str) or not question_text.strip():
            raise AIResponseError("AI provider returned a question with no text")

        if question_type not in ALLOWED_QUESTION_TYPES:
            raise AIResponseError(f"AI provider returned an unexpected question_type: {question_type}")

        cleaned_questions.append({
            "question_text": question_text.strip(),
            "question_type": question_type
        })

    # in case the model ignores the requested count
    return cleaned_questions[:number_of_questions]
