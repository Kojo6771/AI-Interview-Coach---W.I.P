from app.models.user import User


def test_user_model_uses_existing_database_hash_column_name():
    """The ORM should map to the column name the database already exposes."""
    assert "hashed_password" in User.__table__.columns.keys()
