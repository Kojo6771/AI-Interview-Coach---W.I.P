import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import (
    Answer,
    CVDocument,
    Feedback,
    InterviewQuestion,
    InterviewSession,
    User,
)
from app.routes import dependencies


@pytest.fixture
def database(tmp_path):
    test_url = os.getenv("TEST_DATABASE_URL")
    schema = None
    admin_engine = None
    if test_url and test_url.startswith(("postgresql://", "postgresql+")):
        admin_engine = create_engine(test_url)
        schema = f"ai_eval_test_{uuid4().hex}"
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(
            test_url,
            connect_args={"options": f"-csearch_path={schema}"},
        )
    else:
        engine = create_engine(
            f"sqlite:///{tmp_path / 'interview-tests.sqlite3'}",
            connect_args={"check_same_thread": False},
        )

    try:
        Base.metadata.create_all(bind=engine)
        test_session = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

        def override_get_db():
            session = test_session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db
        yield engine, test_session
    finally:
        app.dependency_overrides.clear()
        if engine:
            Base.metadata.drop_all(bind=engine)
            engine.dispose()
        if admin_engine is not None and schema is not None:
            with admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin_engine.dispose()


@pytest.fixture
def client(database):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth(monkeypatch):
    secret = "integration-test-secret-not-for-production"
    monkeypatch.setattr(dependencies, "Secret_Key", secret)
    monkeypatch.setattr(dependencies, "Algorithm", "HS256")

    def headers(user_id):
        token = jwt.encode(
            {"sub": str(user_id)},
            secret,
            algorithm="HS256",
        )
        return {"Authorization": f"Bearer {token}"}

    return headers


@pytest.fixture
def interview_data(database):
    _, test_session = database
    session = test_session()
    first_user = User(
        username="candidate-one",
        email="candidate-one@example.test",
        hashed_password="not-a-real-password-hash",
    )
    other_user = User(
        username="candidate-two",
        email="candidate-two@example.test",
        hashed_password="not-a-real-password-hash",
    )
    session.add_all([first_user, other_user])
    session.flush()
    cv = CVDocument(
        user_id=first_user.id,
        filename="resume.pdf",
        file_type="pdf",
        extracted_text="Candidate has experience building APIs.",
    )
    session.add(cv)
    session.flush()
    interview = InterviewSession(
        user_id=first_user.id,
        cv_id=cv.id,
        target_role="Backend engineer",
        job_description="Build reliable APIs.",
        interview_type="technical",
        difficulty="intermediate",
        status="created",
    )
    other_cv = CVDocument(
        user_id=other_user.id,
        filename="other.pdf",
        file_type="pdf",
        extracted_text="Other candidate profile.",
    )
    session.add(other_cv)
    session.flush()
    other_interview = InterviewSession(
        user_id=other_user.id,
        cv_id=other_cv.id,
        target_role="Engineer",
        interview_type="technical",
        difficulty="beginner",
        status="created",
    )
    session.add_all([interview, other_interview])
    session.flush()
    question = InterviewQuestion(
        interview_id=interview.id,
        question_text="How would you improve API reliability?",
        question_type="technical",
        difficulty="intermediate",
        order_number=1,
    )
    other_question = InterviewQuestion(
        interview_id=other_interview.id,
        question_text="Describe your work.",
        question_type="behavioural",
        difficulty="beginner",
        order_number=1,
    )
    session.add_all([question, other_question])
    session.flush()
    answer = Answer(
        question_id=question.id,
        interview_id=interview.id,
        answer_text="I would add retries with bounded backoff.",
    )
    session.add(answer)
    session.commit()
    ids = {
        "user_id": first_user.id,
        "other_user_id": other_user.id,
        "cv_id": cv.id,
        "interview_id": interview.id,
        "other_interview_id": other_interview.id,
        "question_id": question.id,
        "other_question_id": other_question.id,
        "answer_id": answer.id,
    }
    session.close()
    return ids
