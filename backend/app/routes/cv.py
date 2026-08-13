from pathlib import Path

from fastapi import(
    APIRouter,
    File,
    UploadFile,
    HTTPException,
    Depends,
    status,
)

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.cv import CVDocument
from app.services.cv_parser import extract_cv_text
from app.schemas.cv import  CVResponse

# IMPORTANT:
# Replace this import with the SAME get_current_user import
# used by your working GET /users/me endpoint.
from app.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/cvs",
    tags=["CVs"],
)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx"
}