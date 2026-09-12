from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cv import CVDocument
from app.models.interview_session import InterviewSession
from app.models.interview_question import InterviewQuestion
from app.models.user import User
from app.schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewDetailResponse
)
from app.schemas.question import QuestionCreate, QuestionResponse
from app.services.ai_service import (
    AIResponseError,
    AIServiceError,
    generate_interview_questions as ai_generate_questions
)

from app.routes.dependencies import get_current_user

#router for interview session endpoints
router = APIRouter(
    prefix="/interviews",
    tags=["Interviews"]
)


#shared ownership check reused by the interview and question endpoints below
def _get_owned_interview(
    interview_id: int,
    db: Session,
    current_user: User
) -> InterviewSession:
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
    return _get_owned_interview(interview_id, db, current_user)


#uses the CV linked to the interview to generate AI-personalised questions
@router.post(
    "/{interview_id}/questions/generate",
    response_model=list[QuestionResponse],
    status_code=status.HTTP_201_CREATED
)
def generate_interview_questions(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(interview_id, db, current_user)

    existing_question = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview.id)
        .first()
    )

    if existing_question is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Questions have already been generated for this interview."
        )

    cv = (
        db.query(CVDocument)
        .filter(CVDocument.id == interview.cv_id)
        .first()
    )

    if cv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found"
        )

    if not cv.extracted_text or not cv.extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CV text is missing for this CV. Please re-upload it."
        )

    try:
        generated_questions = ai_generate_questions(
            cv_text=cv.extracted_text,
            target_role=interview.target_role,
            job_description=interview.job_description,
            interview_type=interview.interview_type,
            difficulty=interview.difficulty
        )

    except AIServiceError as e:
        print("AI SERVICE ERROR:", repr(e))

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service is currently unavailable. Please try again later."
        )

    except AIResponseError as e:
        print("AI RESPONSE ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Received an invalid response while generating questions."
        )

    new_questions = []

    for index, generated in enumerate(generated_questions):
        try:
            validated = QuestionCreate(
                question_text=generated["question_text"],
                question_type=generated["question_type"],
                difficulty=interview.difficulty,
                order_number=index + 1
            )

        except ValidationError as e:
            print("AI RESPONSE ERROR:", repr(e))

            raise HTTPException(
                status_code=500,
                detail="Received an invalid response while generating questions."
            )

        new_questions.append(
            InterviewQuestion(
                interview_id=interview.id,
                question_text=validated.question_text,
                question_type=validated.question_type,
                difficulty=validated.difficulty,
                order_number=validated.order_number
            )
        )

    db.add_all(new_questions)

    try:
        db.commit()

        for question in new_questions:
            db.refresh(question)

    except Exception as e:
        db.rollback()

        print("DATABASE ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Failed to generate questions"
        )

    return new_questions


#question get endpoint to retrieve all questions for an interview, ordered for presentation
@router.get(
    "/{interview_id}/questions",
    response_model=list[QuestionResponse],
    status_code=status.HTTP_200_OK
)
def get_interview_questions(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(interview_id, db, current_user)

    questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview.id)
        .order_by(InterviewQuestion.order_number.asc())
        .all()
    )

    return questions


@router.get(
    "/{interview_id}/questions/{question_id}",
    response_model=QuestionResponse,
    status_code=status.HTTP_200_OK
)
def get_interview_question(
    interview_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(interview_id, db, current_user)

    question = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.id == question_id,
            InterviewQuestion.interview_id == interview.id
        )
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    return question
