import logging

from fastapi import FastAPI
from app.routes import auth, users, cv, interviews


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

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
app.include_router(interviews.router)  # Include the interviews router for interview session endpoints

# Root endpoint for a simple welcome message and health check.
@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Interview Coach API!"}
