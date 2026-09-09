# Temporary sample question generator, used to validate the DB/API flow before AI generation is added.
# Replace this module's logic with a real AI call later without changing the route layer.
from app.models.interview_session import InterviewSession


def generate_sample_questions(interview: InterviewSession) -> list[dict]:
    role = interview.target_role or "this role"

    return [
        {
            "question_text": f"Tell me about your experience relevant to the {role} role.",
            "question_type": "behavioural"
        },
        {
            "question_text": f"How would you design a scalable system for a {role} position?",
            "question_type": "technical"
        },
        {
            "question_text": "Describe a challenging problem you solved and the steps you took.",
            "question_type": "situational"
        },
        {
            "question_text": f"What tools or approaches do you rely on most as a {role}?",
            "question_type": "technical"
        },
        {
            "question_text": "Tell me about a time you had to learn something new quickly under pressure.",
            "question_type": "behavioural"
        }
    ]
