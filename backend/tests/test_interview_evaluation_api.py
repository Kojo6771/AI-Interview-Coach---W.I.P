from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import threading

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as OrmSession

from app.models import Answer, Feedback, InterviewQuestion, InterviewSession
from app.routes import interviews
from app.services.ai_service import AIServiceError


def _evaluation(**overrides):
    result = {
        "score": 80,
        "strengths": ["Relevant answer"],
        "improvements": ["Add a concrete result"],
        "feedback_text": "The response is relevant and technically sound.",
        "improved_answer": "I would add bounded retries and monitor failures."
    }
    result.update(overrides)
    return result


def _evaluate(client, auth, ids, route="evaluate"):
    return client.post(
        f"/interviews/{ids['interview_id']}/questions/"
        f"{ids['question_id']}/{route}",
        headers=auth(ids["user_id"]),
    )


def test_authentication_ownership_and_missing_resources(
    client, auth, interview_data
):
    ids = interview_data
    url = (
        f"/interviews/{ids['interview_id']}/questions/"
        f"{ids['question_id']}/evaluate"
    )
    assert client.post(url).status_code == 401

    wrong_owner = client.post(
        f"/interviews/{ids['other_interview_id']}/questions/"
        f"{ids['other_question_id']}/evaluate",
        headers=auth(ids["user_id"]),
    )
    assert wrong_owner.status_code == 404

    nonexistent_question = client.post(
        f"/interviews/{ids['interview_id']}/questions/99999/evaluate",
        headers=auth(ids["user_id"]),
    )
    assert nonexistent_question.status_code == 404

    no_answer = client.post(
        f"/interviews/{ids['other_interview_id']}/questions/"
        f"{ids['other_question_id']}/evaluate",
        headers=auth(ids["other_user_id"]),
    )
    assert no_answer.status_code == 404


def test_interview_question_generation_and_answer_submission_still_work(
    client, auth, interview_data, monkeypatch
):
    ids = interview_data
    monkeypatch.setattr(
        interviews,
        "ai_generate_questions",
        lambda **_: [
            {
                "question_text": "How do you make an API reliable?",
                "question_type": "technical",
            }
        ],
    )
    created = client.post(
        "/interviews",
        json={
            "cv_id": ids["cv_id"],
            "target_role": "Backend engineer",
            "job_description": "Own API reliability.",
            "interview_type": "technical",
            "difficulty": "intermediate",
        },
        headers=auth(ids["user_id"]),
    )
    assert created.status_code == 201
    new_interview_id = created.json()["id"]
    generated = client.post(
        f"/interviews/{new_interview_id}/questions/generate",
        headers=auth(ids["user_id"]),
    )
    assert generated.status_code == 201
    question_id = generated.json()[0]["id"]
    submitted = client.post(
        f"/interviews/{new_interview_id}/questions/{question_id}/answer",
        json={"answer_text": "I use bounded retries and monitoring."},
        headers=auth(ids["user_id"]),
    )
    assert submitted.status_code == 201


def test_evaluation_is_saved_repeats_conflict_and_answer_update_invalidates(
    client, auth, interview_data, monkeypatch
):
    ids = interview_data
    monkeypatch.setattr(
        interviews, "ai_evaluate_answer", lambda **_: _evaluation()
    )

    first = _evaluate(client, auth, ids)
    assert first.status_code == 201
    feedback_id = first.json()["id"]
    assert first.json()["score"] == 80

    assert _evaluate(client, auth, ids).status_code == 409
    stored = client.get(
        f"/interviews/{ids['interview_id']}/questions/"
        f"{ids['question_id']}/feedback",
        headers=auth(ids["user_id"]),
    )
    assert stored.status_code == 200
    assert stored.json()["evaluation"]["id"] == feedback_id

    updated = client.put(
        f"/interviews/{ids['interview_id']}/questions/"
        f"{ids['question_id']}/answer",
        json={"answer_text": "I would use a circuit breaker and monitor errors."},
        headers=auth(ids["user_id"]),
    )
    assert updated.status_code == 200
    assert client.get(
        f"/interviews/{ids['interview_id']}/questions/"
        f"{ids['question_id']}/feedback",
        headers=auth(ids["user_id"]),
    ).status_code == 404

    reevaluated = _evaluate(client, auth, ids)
    assert reevaluated.status_code == 201
    refreshed = client.get(
        f"/interviews/{ids['interview_id']}/questions/"
        f"{ids['question_id']}/feedback",
        headers=auth(ids["user_id"]),
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["evaluation"]["answer_id"] == ids["answer_id"]


def test_outdated_evaluation_is_rejected_after_answer_changes(
    client, auth, interview_data, database, monkeypatch
):
    ids = interview_data
    _, test_session = database

    def update_while_ai_is_waiting(**_):
        session = test_session()
        answer = session.get(Answer, ids["answer_id"])
        answer.answer_text = "Updated while the evaluation was running."
        answer.answer_revision += 1
        answer.evaluation_token = None
        answer.evaluation_started_at = None
        session.commit()
        session.close()
        return _evaluation()

    monkeypatch.setattr(
        interviews, "ai_evaluate_answer", update_while_ai_is_waiting
    )
    response = _evaluate(client, auth, ids)
    assert response.status_code == 409

    session = test_session()
    assert session.scalar(select(Feedback).where(Feedback.answer_id == ids["answer_id"])) is None
    answer = session.get(Answer, ids["answer_id"])
    assert answer.answer_text == "Updated while the evaluation was running."
    assert answer.answer_revision == 2
    session.close()


def test_failed_evaluation_releases_reservation_and_can_be_retried(
    client, auth, interview_data, database, monkeypatch
):
    ids = interview_data
    _, test_session = database
    calls = 0

    def fail_then_succeed(**_):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise AIServiceError("private provider detail")
        return _evaluation()

    monkeypatch.setattr(interviews, "ai_evaluate_answer", fail_then_succeed)
    failed = _evaluate(client, auth, ids)
    assert failed.status_code == 502
    assert "private provider detail" not in failed.text
    session = test_session()
    answer = session.get(Answer, ids["answer_id"])
    assert answer.evaluation_token is None
    assert answer.evaluation_started_at is None
    session.close()

    assert _evaluate(client, auth, ids).status_code == 201
    assert calls == 2


def test_stale_reservation_is_recovered(
    client, auth, interview_data, database, monkeypatch
):
    ids = interview_data
    _, test_session = database
    session = test_session()
    answer = session.get(Answer, ids["answer_id"])
    answer.evaluation_token = "old-reservation-token"
    answer.evaluation_started_at = datetime.now(timezone.utc) - timedelta(hours=1)
    session.commit()
    session.close()

    monkeypatch.setattr(
        interviews, "ai_evaluate_answer", lambda **_: _evaluation()
    )
    response = _evaluate(client, auth, ids)
    assert response.status_code == 201


def test_database_failure_does_not_persist_partial_feedback(
    client, auth, interview_data, database, monkeypatch
):
    ids = interview_data
    _, test_session = database
    monkeypatch.setattr(
        interviews, "ai_evaluate_answer", lambda **_: _evaluation()
    )
    original_commit = OrmSession.commit

    def fail_feedback_commit(session):
        if any(isinstance(item, Feedback) for item in session.new):
            raise SQLAlchemyError("simulated persistence failure")
        return original_commit(session)

    monkeypatch.setattr(OrmSession, "commit", fail_feedback_commit)
    response = _evaluate(client, auth, ids)
    assert response.status_code == 500

    session = test_session()
    assert session.scalar(select(Feedback).where(Feedback.answer_id == ids["answer_id"])) is None
    answer = session.get(Answer, ids["answer_id"])
    assert answer.evaluation_token is None
    session.close()


def test_results_and_completion_require_every_answer_and_evaluation(
    client, auth, interview_data, database, monkeypatch
):
    ids = interview_data
    _, test_session = database
    session = test_session()
    second_question = InterviewQuestion(
        interview_id=ids["interview_id"],
        question_text="How would you monitor this API?",
        question_type="technical",
        difficulty="intermediate",
        order_number=2,
    )
    session.add(second_question)
    session.commit()
    second_question_id = second_question.id
    session.close()

    monkeypatch.setattr(
        interviews, "ai_evaluate_answer", lambda **_: _evaluation()
    )
    result_url = f"/interviews/{ids['interview_id']}/results"
    result = client.get(result_url, headers=auth(ids["user_id"]))
    assert result.status_code == 200
    assert result.json()["total_questions"] == 2
    assert result.json()["submitted_answers"] == 1
    assert result.json()["evaluated_answers"] == 0
    assert result.json()["average_score"] is None
    assert result.json()["remaining_questions"] == 1
    assert result.json()["ready_for_completion"] is False

    complete_url = f"/interviews/{ids['interview_id']}/complete"
    assert client.post(
        complete_url, headers=auth(ids["user_id"])
    ).status_code == 409
    assert _evaluate(client, auth, ids).status_code == 201

    partially_evaluated = client.get(
        result_url, headers=auth(ids["user_id"])
    ).json()
    assert partially_evaluated["evaluated_answers"] == 1
    assert partially_evaluated["ready_for_completion"] is False

    second_answer = client.post(
        f"/interviews/{ids['interview_id']}/questions/{second_question_id}/answer",
        json={"answer_text": "I would monitor latency and error rates."},
        headers=auth(ids["user_id"]),
    )
    assert second_answer.status_code == 201
    second_evaluation = client.post(
        f"/interviews/{ids['interview_id']}/questions/{second_question_id}/evaluate",
        headers=auth(ids["user_id"]),
    )
    assert second_evaluation.status_code == 201

    ready = client.get(result_url, headers=auth(ids["user_id"])).json()
    assert ready["submitted_answers"] == 2
    assert ready["evaluated_answers"] == 2
    assert ready["average_score"] == 80.0
    assert ready["ready_for_completion"] is True

    completed = client.post(complete_url, headers=auth(ids["user_id"]))
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"].endswith(("Z", "+00:00"))
    assert client.post(complete_url, headers=auth(ids["user_id"])).json() == completed.json()
    assert client.put(
        f"/interviews/{ids['interview_id']}/questions/"
        f"{ids['question_id']}/answer",
        json={"answer_text": "Cannot edit after completion"},
        headers=auth(ids["user_id"]),
    ).status_code == 409


def test_zero_question_results_are_safe(client, auth, interview_data, database):
    ids = interview_data
    _, test_session = database
    session = test_session()
    empty_interview = InterviewSession(
        user_id=ids["user_id"],
        cv_id=session.get(InterviewSession, ids["interview_id"]).cv_id,
        target_role="Empty interview",
        interview_type="technical",
        difficulty="beginner",
    )
    session.add(empty_interview)
    session.commit()
    interview_id = empty_interview.id
    session.close()

    response = client.get(
        f"/interviews/{interview_id}/results",
        headers=auth(ids["user_id"]),
    )
    assert response.status_code == 200
    assert response.json()["total_questions"] == 0
    assert response.json()["average_score"] is None
    assert response.json()["ready_for_completion"] is False


@pytest.mark.skipif(
    not (
        __import__("os").getenv("TEST_DATABASE_URL", "").startswith(
            ("postgresql://", "postgresql+")
        )
    ),
    reason="Concurrent row-lock behavior requires TEST_DATABASE_URL PostgreSQL",
)
def test_concurrent_requests_reserve_only_one_evaluation(
    auth, interview_data, monkeypatch
):
    ids = interview_data
    provider_started = threading.Event()
    release_provider = threading.Event()
    calls = 0

    def slow_provider(**_):
        nonlocal calls
        calls += 1
        provider_started.set()
        assert release_provider.wait(timeout=10)
        return _evaluation()

    monkeypatch.setattr(interviews, "ai_evaluate_answer", slow_provider)

    def request_evaluation():
        from app.main import app
        from fastapi.testclient import TestClient

        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                f"/interviews/{ids['interview_id']}/questions/"
                f"{ids['question_id']}/evaluate",
                headers=auth(ids["user_id"]),
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_request = executor.submit(request_evaluation)
        assert provider_started.wait(timeout=10)
        second_response = request_evaluation()
        release_provider.set()
        first_response = first_request.result(timeout=10)

    assert sorted([first_response.status_code, second_response.status_code]) == [
        201,
        409,
    ]
    assert calls == 1


@pytest.mark.skipif(
    not (
        __import__("os").getenv("TEST_DATABASE_URL", "").startswith(
            ("postgresql://", "postgresql+")
        )
    ),
    reason="Concurrent row-lock behavior requires TEST_DATABASE_URL PostgreSQL",
)
def test_concurrent_answer_update_invalidates_inflight_evaluation(
    auth, interview_data, database, monkeypatch
):
    ids = interview_data
    provider_started = threading.Event()
    release_provider = threading.Event()
    _, test_session = database

    def slow_provider(**_):
        provider_started.set()
        assert release_provider.wait(timeout=10)
        return _evaluation()

    monkeypatch.setattr(interviews, "ai_evaluate_answer", slow_provider)

    def post_evaluation():
        from app.main import app
        from fastapi.testclient import TestClient

        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                f"/interviews/{ids['interview_id']}/questions/"
                f"{ids['question_id']}/evaluate",
                headers=auth(ids["user_id"]),
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        evaluation = executor.submit(post_evaluation)
        assert provider_started.wait(timeout=10)
        from app.main import app
        from fastapi.testclient import TestClient

        with TestClient(app) as concurrent_client:
            updated = concurrent_client.put(
                f"/interviews/{ids['interview_id']}/questions/"
                f"{ids['question_id']}/answer",
                json={"answer_text": "Answer changed during AI processing."},
                headers=auth(ids["user_id"]),
            )
        release_provider.set()
        evaluation_response = evaluation.result(timeout=10)

    assert updated.status_code == 200
    assert evaluation_response.status_code == 409
    session = test_session()
    assert session.scalar(
        select(Feedback).where(Feedback.answer_id == ids["answer_id"])
    ) is None
    assert session.get(Answer, ids["answer_id"]).evaluation_token is None
    session.close()
