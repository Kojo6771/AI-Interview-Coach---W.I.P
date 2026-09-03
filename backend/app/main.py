from fastapi import FastAPI
from app.routes import auth, users, cv
from app.database import Base, engine
from app.models import User
from app.models import UserProfile
from app.models import Interview
from app.models import Question
from app.models import Answer
from app.models import Feedback
from app.models import CVDocument
from app.models import TargetRole
from app.models import Progress
from app.models import RefreshToken



Base.metadata.create_all(bind=engine)  # Create database tables based on models


# Create the FastAPI application instance.
# This sets API metadata used by automatic docs and client generation.
app = FastAPI(
    title="AI Interview Coach API",
    description=(
        "This API provides endpoints for an AI Interview Coach application, "
        "allowing users to practice interview questions and receive feedback."
    ),
    version="1.0.0",
)

# Register authentication and other related routes from the auth router.
app.include_router(auth.router)
app.include_router(users.router)  # Include the users router for user-related endpoints
app.include_router(cv.router)  # Include the CV router for CV-related endpoints

# Root endpoint for a simple welcome message and health check.
@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Interview Coach API!"}
