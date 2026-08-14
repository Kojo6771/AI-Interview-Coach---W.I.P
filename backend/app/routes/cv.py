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
from app.routes.dependencies import get_current_user
from app.models.user import User

#api router for CV-related endpoints
router = APIRouter(
    prefix="/cvs",
    tags=["CVs"],
)

# Define maximum file size (5 MB)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Define allowed file extensions
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx"
}

# Endpoint to upload a CV file
@router.post(
    "/upload",
    response_model=CVResponse,
    status_code=status.HTTP_201_CREATED,
)

async def upload_cv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    #Check filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded.",
        )

    # Get file extension
    file_extension = Path(file.filename).suffix.lower()

    # Check if file extension is allowed
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed.",
        )

    # Read file content
    file_bytes = await file.read(
        MAX_FILE_SIZE + 1
    )

    await file.close()

    #Check if the file is empty
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    
    # Check file size
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the limit.",
        )

    # Extract text from the CV file
    try:
        extracted_text = extract_cv_text(
            file_bytes=file_bytes,
            file_extension=file_extension
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to extract text from the uploaded file.",
        )

    #Ensure the text exists
    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text could be extracted from the uploaded file.",
        )

    #Make database record for the uploaded CV
    cv = CVDocument(
        user_id=current_user.id,
        filename=file.filename,
        file_type=file_extension.replace(".", ""),
        extracted_text=extracted_text
    )

    db.add(cv)
    db.commit()
    db.refresh(cv)

    return cv

    