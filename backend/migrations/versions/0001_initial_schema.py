"""Create missing application tables without modifying existing tables.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "target_roles" not in existing:
        op.create_table(
            "target_roles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=100), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
        op.create_index(
            op.f("ix_users_username"), "users", ["username"], unique=True
        )
    if "cv_documents" not in existing:
        op.create_table(
            "cv_documents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("file_type", sa.String(length=10), nullable=False),
            sa.Column("file_path", sa.String(length=500), nullable=True),
            sa.Column("extracted_text", sa.Text(), nullable=False),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_cv_documents_id"), "cv_documents", ["id"])
        op.create_index(
            op.f("ix_cv_documents_user_id"), "cv_documents", ["user_id"]
        )
    if "progress" not in existing:
        op.create_table(
            "progress",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("interviews_completed", sa.Integer(), nullable=True),
            sa.Column("average_score", sa.Float(), nullable=True),
            sa.Column("average_communication_score", sa.Float(), nullable=True),
            sa.Column("average_technical_score", sa.Float(), nullable=True),
            sa.Column("average_clarity_score", sa.Float(), nullable=True),
            sa.Column("average_confidence_score", sa.Float(), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if "refresh_tokens" not in existing:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if "user_profiles" not in existing:
        op.create_table(
            "user_profiles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("first_name", sa.String(length=100), nullable=True),
            sa.Column("last_name", sa.String(length=100), nullable=True),
            sa.Column("university", sa.String(length=255), nullable=True),
            sa.Column("degree", sa.String(length=255), nullable=True),
            sa.Column("bio", sa.Text(), nullable=True),
            sa.Column("profile_picture", sa.String(length=500), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )
    if "interview_sessions" not in existing:
        op.create_table(
            "interview_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("cv_id", sa.Integer(), nullable=False),
            sa.Column("target_role", sa.String(length=255), nullable=False),
            sa.Column("job_description", sa.Text(), nullable=True),
            sa.Column("interview_type", sa.String(length=50), nullable=False),
            sa.Column("difficulty", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["cv_id"], ["cv_documents.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_interview_sessions_cv_id"),
            "interview_sessions",
            ["cv_id"],
        )
        op.create_index(
            op.f("ix_interview_sessions_id"), "interview_sessions", ["id"]
        )
        op.create_index(
            op.f("ix_interview_sessions_user_id"),
            "interview_sessions",
            ["user_id"],
        )
    if "interviews" not in existing:
        op.create_table(
            "interviews",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("target_role_id", sa.Integer(), nullable=False),
            sa.Column("cv_id", sa.Integer(), nullable=True),
            sa.Column("interview_type", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("overall_score", sa.Float(), nullable=True),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["cv_id"], ["cv_documents.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["target_role_id"], ["target_roles.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if "interview_questions" not in existing:
        op.create_table(
            "interview_questions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("interview_id", sa.Integer(), nullable=False),
            sa.Column("question_text", sa.Text(), nullable=False),
            sa.Column("question_type", sa.String(length=50), nullable=False),
            sa.Column("difficulty", sa.String(length=50), nullable=False),
            sa.Column("order_number", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["interview_id"], ["interview_sessions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_interview_questions_id"), "interview_questions", ["id"]
        )
        op.create_index(
            op.f("ix_interview_questions_interview_id"),
            "interview_questions",
            ["interview_id"],
        )
    if "questions" not in existing:
        op.create_table(
            "questions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("interview_id", sa.Integer(), nullable=False),
            sa.Column("question_text", sa.Text(), nullable=False),
            sa.Column("question_type", sa.String(length=50), nullable=False),
            sa.Column("difficulty", sa.String(length=50), nullable=True),
            sa.Column("question_order", sa.Integer(), nullable=False),
            sa.Column("generated_by", sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(
                ["interview_id"], ["interviews.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if "answers" not in existing:
        op.create_table(
            "answers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("question_id", sa.Integer(), nullable=False),
            sa.Column("interview_id", sa.Integer(), nullable=False),
            sa.Column("answer_text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column("answer_revision", sa.Integer(), nullable=False),
            sa.Column("evaluation_token", sa.String(length=36), nullable=True),
            sa.Column(
                "evaluation_started_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.ForeignKeyConstraint(
                ["interview_id"], ["interview_sessions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["question_id"], ["interview_questions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_answers_interview_id"), "answers", ["interview_id"]
        )
        op.create_index(
            op.f("ix_answers_question_id"), "answers", ["question_id"], unique=True
        )
    if "feedback" not in existing:
        op.create_table(
            "feedback",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("answer_id", sa.Integer(), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("strengths", sa.JSON(), nullable=False),
            sa.Column("improvements", sa.JSON(), nullable=False),
            sa.Column("feedback_text", sa.Text(), nullable=False),
            sa.Column("improved_answer", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["answer_id"], ["answers.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_feedback_answer_id"), "feedback", ["answer_id"], unique=True
        )


def downgrade() -> None:
    # This bootstrap baseline deliberately preserves all tables and user data.
    pass
