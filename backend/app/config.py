from dotenv import load_dotenv
from pathlib import Path
import os

# Load environment variables from .env file
load_dotenv()

# Get the database URL from environment variables, with a safe fallback for local development
Database_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

Secret_Key = os.getenv("SECRET_KEY")
Algorithm = os.getenv("ALGORITHM")
Access_Token_Expire_Minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Used by app/services/ai_service.py to call the OpenAI API
OpenAI_Api_Key = os.getenv("OPENAI_API_KEY")
OpenAI_Request_Timeout_Seconds = float(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "30"))
OpenAI_Max_Retries = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
Evaluation_Reservation_Timeout_Seconds = int(
    os.getenv("EVALUATION_RESERVATION_TIMEOUT_SECONDS", "900")
)

if OpenAI_Request_Timeout_Seconds <= 0:
    raise ValueError("OPENAI_REQUEST_TIMEOUT_SECONDS must be positive")
if OpenAI_Max_Retries < 0:
    raise ValueError("OPENAI_MAX_RETRIES cannot be negative")
if OpenAI_Max_Retries > 5:
    raise ValueError("OPENAI_MAX_RETRIES cannot exceed 5")
if Evaluation_Reservation_Timeout_Seconds <= 0:
    raise ValueError("EVALUATION_RESERVATION_TIMEOUT_SECONDS must be positive")