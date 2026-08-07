#Import necessary modules from SQLAlchemy
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from .env file
from app.config import Database_URL

engine = create_engine(Database_URL, echo=True)  # Set echo=True for SQL query logging

# Create a configured "Session" class
SessionLocal = sessionmaker(
    autocommit = False,
    autoflush = False,
    bind = engine
)

Base = declarative_base()

# Dependency to get a database session
def get_db():
    db = SessionLocal()

    # Ensure that the database session is closed after use, even if an error occurs.
    try:
        yield db
    finally:
        db.close()