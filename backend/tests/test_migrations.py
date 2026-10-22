from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app import config as app_config
from app.database import Base
from app.models import Answer, CVDocument, Feedback, InterviewQuestion, InterviewSession, User


def test_upgrade_preserves_existing_feedback_and_adds_missing_columns(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "legacy.sqlite3"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setattr(app_config, "Database_URL", database_url)
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        user = User(
            username="migration-user",
            email="migration-user@example.test",
            hashed_password="not-a-real-password-hash",
        )
        session.add(user)
        session.flush()
        cv = CVDocument(
            user_id=user.id,
            filename="cv.pdf",
            file_type="pdf",
            extracted_text="Candidate information",
        )
        session.add(cv)
        session.flush()
        interview = InterviewSession(
            user_id=user.id,
            cv_id=cv.id,
            target_role="Engineer",
            interview_type="technical",
            difficulty="beginner",
        )
        session.add(interview)
        session.flush()
        question = InterviewQuestion(
            interview_id=interview.id,
            question_text="Question",
            question_type="technical",
            difficulty="beginner",
            order_number=1,
        )
        session.add(question)
        session.flush()
        answer = Answer(
            question_id=question.id,
            interview_id=interview.id,
            answer_text="Existing answer",
        )
        session.add(answer)
        session.flush()
        feedback = Feedback(
            answer_id=answer.id,
            score=75,
            strengths=["Clear"],
            improvements=["Add evidence"],
            feedback_text="Existing feedback",
            improved_answer="Existing improved answer",
        )
        session.add(feedback)
        session.commit()
        answer_id = answer.id
        feedback_id = feedback.id

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE legacy_answers_copy ("
                "id INTEGER PRIMARY KEY, "
                "question_id INTEGER NOT NULL, "
                "answer_text TEXT, "
                "audio_path VARCHAR(500), "
                "submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "FOREIGN KEY(question_id) REFERENCES questions(id))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO legacy_answers_copy "
                "(id, question_id, answer_text, submitted_at) "
                "SELECT id, question_id, answer_text, created_at FROM answers"
            )
        )
        connection.execute(text("DROP TABLE answers"))
        connection.execute(
            text("ALTER TABLE legacy_answers_copy RENAME TO answers")
        )
        connection.execute(
            text("ALTER TABLE interview_sessions DROP COLUMN completed_at")
        )

    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    inspector = inspect(engine)
    assert {
        "answer_revision",
        "evaluation_token",
        "evaluation_started_at",
    }.issubset({column["name"] for column in inspector.get_columns("answers")})
    assert "completed_at" in {
        column["name"]
        for column in inspector.get_columns("interview_sessions")
    }
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT answer_text FROM legacy_answers WHERE id = :id"),
            {"id": answer_id},
        ).scalar_one() == "Existing answer"
        assert connection.execute(
            text("SELECT feedback_text FROM legacy_feedback WHERE id = :id"),
            {"id": feedback_id},
        ).scalar_one() == "Existing feedback"
        assert connection.execute(text("SELECT COUNT(*) FROM answers")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM feedback")).scalar_one() == 0

    command.downgrade(alembic_config, "-1")
    assert "evaluation_started_at" in {
        column["name"] for column in inspect(engine).get_columns("answers")
    }
    engine.dispose()
