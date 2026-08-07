from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the database URL from environment variables, with a safe fallback for local development
Database_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")