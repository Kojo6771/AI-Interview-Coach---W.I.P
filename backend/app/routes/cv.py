from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status
)

from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cv import CVDocument
from app.models.user import User
from app.schemas.cv import CVResponse
from app.services.cv_parser import extract_cv_text

# Use the same import you use for GET /users/me
from app.routes.dependencies import get_current_user

#router for CV-related endpoints
router = APIRouter(
    prefix="/cvs",
    tags=["CVs"]
)


MAX_FILE_SIZE = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx"
}


@router.post(
    "/upload",
    response_model=CVResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_cv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File must have a filename"
        )

    # Get extension
    extension = Path(file.filename).suffix.lower()

    # Validate extension
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are allowed"
        )

    # Read file
    file_bytes = await file.read(
        MAX_FILE_SIZE + 1
    )

    await file.close()

    # Check empty file
    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    # Check size
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="CV must be 5 MB or smaller"
        )

    # Extract text
    try:
        extracted_text = extract_cv_text(
            file_bytes=file_bytes,
            file_extension=extension
        )

    except Exception as e:
        print("CV PARSER ERROR:", repr(e))

        raise HTTPException(
            status_code=400,
            detail=f"Unable to read CV: {str(e)}"
        )

    # Make sure text was found
    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail=(
                "No text could be extracted from the CV. "
                "The file may be scanned or image-based."
            )
        )

    # Create CV database entry
    cv = CVDocument(
        user_id=current_user.id,
        filename=file.filename,
        file_type=extension.replace(".", ""),
        file_path=None,
        extracted_text=extracted_text
    )

    # Save to database
    db.add(cv)

    try:
        db.commit()
        db.refresh(cv)

    except Exception as e:
        db.rollback()

        print("DATABASE ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Failed to save CV"
        )

    return cv

#CV get endpoint to retrieve all CVs for the current user
@router.get(
    "",
    response_model=list[CVResponse],
    status_code=status.HTTP_200_OK
)
def get_user_cvs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cvs = (
        db.query(CVDocument)
        .filter(CVDocument.user_id == current_user.id)
        .order_by(CVDocument.uploaded_at.desc())
        .all()
    )

    return cvs