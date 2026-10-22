"""Add answer evaluation and interview completion columns safely.

Revision ID: 0002_evaluation
Revises: 0001_initial
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "0002_evaluation"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> bool:
    inspector = inspect(op.get_bind())
    existing = {item["name"] for item in inspector.get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)
        return True
    return False


def _add_foreign_key_if_missing(
    table: str,
    column: str,
    referred_table: str,
    constraint_name: str,
    ondelete: str,
) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    exists = any(
        key.get("constrained_columns") == [column]
        and key.get("referred_table") == referred_table
        and key.get("referred_columns") == ["id"]
        for key in inspector.get_foreign_keys(table)
    )
    if exists:
        return

    orphan_count = bind.execute(
        text(
            f'SELECT COUNT(*) FROM "{table}" child '
            f'WHERE child."{column}" IS NOT NULL AND NOT EXISTS '
            f'(SELECT 1 FROM "{referred_table}" parent '
            f'WHERE parent.id = child."{column}")'
        )
    ).scalar_one()
    if orphan_count:
        raise RuntimeError(
            f"Cannot add {constraint_name}: {orphan_count} orphan references exist"
        )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table) as batch:
            batch.create_foreign_key(
                constraint_name,
                referred_table,
                [column],
                ["id"],
                ondelete=ondelete,
            )
    else:
        op.create_foreign_key(
            constraint_name,
            table,
            referred_table,
            [column],
            ["id"],
            ondelete=ondelete,
        )


def _archive_legacy_table(table: str, archived_table: str) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table(archived_table):
        raise RuntimeError(
            f"Cannot preserve legacy {table}: {archived_table} already exists"
        )

    indexes = inspector.get_indexes(table)
    if bind.dialect.name == "postgresql":
        names = {index["name"] for index in indexes}
        primary_key_name = inspector.get_pk_constraint(table).get("name")
        if primary_key_name:
            names.add(primary_key_name)
        existing_index_names = set()
        for existing_table in inspector.get_table_names():
            existing_index_names.update(
                index["name"]
                for index in inspector.get_indexes(existing_table)
            )
            primary = inspector.get_pk_constraint(existing_table).get("name")
            if primary:
                existing_index_names.add(primary)
            existing_index_names.update(
                constraint["name"]
                for constraint in inspector.get_unique_constraints(existing_table)
                if constraint.get("name")
            )
        for index_name in names:
            archived_index_name = f"legacy_{index_name}"
            if archived_index_name in existing_index_names:
                raise RuntimeError(
                    f"Cannot preserve legacy index {index_name}: "
                    f"{archived_index_name} already exists"
                )
            preparer = bind.dialect.identifier_preparer
            op.execute(
                sa.text(
                    f"ALTER INDEX {preparer.quote(index_name)} "
                    f"RENAME TO {preparer.quote(archived_index_name)}"
                )
            )
        sequence_name = f"{table}_id_seq"
        archived_sequence_name = f"{archived_table}_id_seq"
        if inspector.has_sequence(sequence_name):
            if inspector.has_sequence(archived_sequence_name):
                raise RuntimeError(
                    f"Cannot preserve legacy sequence {sequence_name}: "
                    f"{archived_sequence_name} already exists"
                )
            preparer = bind.dialect.identifier_preparer
            op.execute(
                sa.text(
                    f"ALTER SEQUENCE {preparer.quote(sequence_name)} "
                    f"RENAME TO {preparer.quote(archived_sequence_name)}"
                )
            )
    elif bind.dialect.name == "sqlite":
        for index in indexes:
            op.drop_index(index["name"], table_name=table)

    op.rename_table(table, archived_table)

    if bind.dialect.name == "sqlite":
        for index in indexes:
            op.create_index(
                f"legacy_{index['name']}",
                archived_table,
                index["column_names"],
                unique=index["unique"],
            )


def _create_current_feedback_table() -> None:
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
        sa.ForeignKeyConstraint(["answer_id"], ["answers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feedback_answer_id"), "feedback", ["answer_id"], unique=True
    )


def _create_current_answer_table() -> None:
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
    op.create_index(op.f("ix_answers_interview_id"), "answers", ["interview_id"])
    op.create_index(
        op.f("ix_answers_question_id"), "answers", ["question_id"], unique=True
    )


def _replace_incompatible_evaluation_tables() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table("answers"):
        return

    answer_columns = {column["name"] for column in inspector.get_columns("answers")}
    required_answer_columns = {
        "id",
        "question_id",
        "interview_id",
        "answer_text",
        "created_at",
        "updated_at",
    }
    answer_foreign_keys = inspector.get_foreign_keys("answers")
    question_fk_matches = any(
        key.get("constrained_columns") == ["question_id"]
        and key.get("referred_table") == "interview_questions"
        for key in answer_foreign_keys
    )
    if not required_answer_columns.issubset(answer_columns) or not question_fk_matches:
        _archive_legacy_table("answers", "legacy_answers")
        if inspector.has_table("feedback"):
            _archive_legacy_table("feedback", "legacy_feedback")
        _create_current_answer_table()
        _create_current_feedback_table()
        return

    if not inspector.has_table("feedback"):
        _create_current_feedback_table()
        return

    feedback_columns = {
        column["name"] for column in inspector.get_columns("feedback")
    }
    required_feedback_columns = {
        "id",
        "answer_id",
        "score",
        "strengths",
        "improvements",
        "feedback_text",
        "improved_answer",
        "created_at",
        "updated_at",
    }
    if not required_feedback_columns.issubset(feedback_columns):
        _archive_legacy_table("feedback", "legacy_feedback")
        _create_current_feedback_table()


def upgrade() -> None:
    _replace_incompatible_evaluation_tables()

    _add_foreign_key_if_missing(
        "interviews",
        "user_id",
        "users",
        "interviews_user_id_fkey",
        "CASCADE",
    )
    _add_foreign_key_if_missing(
        "interviews",
        "cv_id",
        "cv_documents",
        "interviews_cv_id_fkey",
        "SET NULL",
    )
    _add_foreign_key_if_missing(
        "progress",
        "user_id",
        "users",
        "progress_user_id_fkey",
        "CASCADE",
    )
    _add_foreign_key_if_missing(
        "refresh_tokens",
        "user_id",
        "users",
        "refresh_tokens_user_id_fkey",
        "CASCADE",
    )
    _add_foreign_key_if_missing(
        "user_profiles",
        "user_id",
        "users",
        "user_profiles_user_id_fkey",
        "CASCADE",
    )

    added_revision = _add_column_if_missing(
        "answers",
        sa.Column(
            "answer_revision",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    if added_revision:
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table("answers") as batch:
                batch.alter_column("answer_revision", server_default=None)
        else:
            op.alter_column(
                "answers", "answer_revision", server_default=None
            )
    _add_column_if_missing(
        "answers",
        sa.Column("evaluation_token", sa.String(length=36), nullable=True),
    )
    _add_column_if_missing(
        "answers",
        sa.Column("evaluation_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        "interview_sessions",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    inspector = inspect(op.get_bind())
    constraints = inspector.get_unique_constraints("feedback")
    indexes = inspector.get_indexes("feedback")
    answer_id_is_unique = any(
        constraint.get("column_names") == ["answer_id"]
        for constraint in constraints
    ) or any(
        index.get("column_names") == ["answer_id"] and index.get("unique")
        for index in indexes
    )
    if not answer_id_is_unique:
        duplicate = op.get_bind().execute(
            text(
                "SELECT answer_id FROM feedback "
                "GROUP BY answer_id HAVING COUNT(*) > 1 LIMIT 1"
            )
        ).first()
        if duplicate is not None:
            raise RuntimeError(
                "Cannot add one-feedback-per-answer constraint: duplicate feedback exists"
            )
        op.create_index(
            "ix_feedback_answer_id", "feedback", ["answer_id"], unique=True
        )


def downgrade() -> None:
    # Evaluation metadata and completion timestamps are retained on downgrade
    # to avoid dropping potentially useful data from an existing installation.
    pass
