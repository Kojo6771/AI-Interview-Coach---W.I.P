from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cv import CVDocument
from app.models.interview_session import InterviewSession
from app.models.user import User
from app.schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewDetailResponse
)

from app.routes.dependencies import get_current_user

#router for interview session endpoints
router = APIRouter(
    prefix="/interviews",
    tags=["Interviews"]
)


@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED
)
def create_interview(
    interview: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify the CV exists and belongs to the current user
    cv = (
        db.query(CVDocument)
        .filter(
            CVDocument.id == interview.cv_id,
            CVDocument.user_id == current_user.id
        )
        .first()
    )

    if cv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )

    new_interview = InterviewSession(
        user_id=current_user.id,
        cv_id=interview.cv_id,
        target_role=interview.target_role,
        job_description=interview.job_description,
        interview_type=interview.interview_type,
        difficulty=interview.difficulty
    )

    db.add(new_interview)

    try:
        db.commit()
        db.refresh(new_interview)

    except Exception as e:
        db.rollback()

        print("DATABASE ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Failed to create interview session"
        )

    return new_interview


#interview get endpoint to retrieve all interview sessions for the current user
@router.get(
    "",
    response_model=list[InterviewResponse],
    status_code=status.HTTP_200_OK
)
def get_user_interviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interviews = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )

    return interviews


@router.get(
    "/{interview_id}",
    response_model=InterviewDetailResponse,
    status_code=status.HTTP_200_OK
)
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.id == interview_id,
            InterviewSession.user_id == current_user.id
        )
        .first()
    )

    # 404 whether the interview doesn't exist or belongs to another user,
    # so we don't leak the existence of other users' interviews
    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    return interview
