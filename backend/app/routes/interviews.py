# Routes for managing interview sessions, questions, and answers.
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

# Standard library imports
import logging
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

#App imports
from app.database import get_db
from app.models.answer import Answer
from app.models.cv import CVDocument
from app.models.feedback import Feedback
from app.models.interview_session import InterviewSession
from app.models.interview_question import InterviewQuestion
from app.models.user import User
from app.schemas.answer import (
    AnswerCreate,
    AnswerResponse,
    AnswerUpdate,
    InterviewAnswerResponse
)
from app.schemas.feedback import FeedbackResponse, QuestionAnswerFeedbackResponse
from app.schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewDetailResponse,
    InterviewResultsResponse
)
from app.schemas.question import QuestionCreate, QuestionResponse
from app.services.ai_service import (
    AIResponseError,
    AIServiceError,
    evaluate_interview_answer as ai_evaluate_answer,
    generate_interview_questions as ai_generate_questions
)

from app.routes.dependencies import get_current_user
from app.config import Evaluation_Reservation_Timeout_Seconds
from app.schemas.feedback import AIEvaluationResult


logger = logging.getLogger(__name__)


#router for interview session endpoints
router = APIRouter(
    prefix="/interviews",
    tags=["Interviews"]
)


#shared ownership check reused by the interview and question endpoints below
def _get_owned_interview(
    interview_id: int,
    db: Session,
    current_user: User,
    lock: bool = False
) -> InterviewSession:
    query = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.id == interview_id,
            InterviewSession.user_id == current_user.id
        )
    )
    if lock:
        query = query.with_for_update().populate_existing()
    interview = query.first()

    # 404 whether the interview doesn't exist or belongs to another user,
    # so we don't leak the existence of other users' interviews
    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )

    return interview


def _valid_feedback(feedback: Feedback) -> bool:
    try:
        AIEvaluationResult(
            score=feedback.score,
            strengths=feedback.strengths,
            improvements=feedback.improvements,
            feedback=feedback.feedback_text,
            improved_answer=feedback.improved_answer
        )
    except ValidationError:
        return False
    return True


def _release_evaluation_reservation(
    db: Session,
    answer_id: int,
    token: str
) -> None:
    try:
        db.query(Answer).filter(
            Answer.id == answer_id,
            Answer.evaluation_token == token
        ).update(
            {
                Answer.evaluation_token: None,
                Answer.evaluation_started_at: None
            },
            synchronize_session=False
        )
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.error(
            "Failed to release evaluation reservation for answer %s: %s",
            answer_id,
            type(error).__name__
        )


#shared ownership check reused by the answer endpoints below
def _get_owned_question(
    interview: InterviewSession,
    question_id: int,
    db: Session
) -> InterviewQuestion:
    question = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.id == question_id,
            InterviewQuestion.interview_id == interview.id
        )
        .first()
    )

    # 404 whether the question doesn't exist or belongs to a different interview,
    # so a client can't probe which question ids belong to other interviews
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    return question


#shared ownership check reused by the evaluate/feedback endpoints below
def _get_owned_answer(
    question: InterviewQuestion,
    db: Session
) -> Answer:
    answer = (
        db.query(Answer)
        .filter(Answer.question_id == question.id)
        .first()
    )

    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No answer has been submitted for this question yet"
        )

    return answer


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

    except SQLAlchemyError as e:
        db.rollback()

        logger.error("Interview creation failed: %s", type(e).__name__)

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


@router.get(
    "/{interview_id}/results",
    response_model=InterviewResultsResponse,
    status_code=status.HTTP_200_OK
)
def get_interview_results(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(interview_id, db, current_user)
    rows = (
        db.query(InterviewQuestion, Answer, Feedback)
        .outerjoin(Answer, Answer.question_id == InterviewQuestion.id)
        .outerjoin(Feedback, Feedback.answer_id == Answer.id)
        .filter(InterviewQuestion.interview_id == interview.id)
        .all()
    )
    total_questions = len(rows)
    submitted_answers = sum(answer is not None for _, answer, _ in rows)
    valid_scores = [
        feedback.score
        for _, answer, feedback in rows
        if answer is not None
        and feedback is not None
        and _valid_feedback(feedback)
    ]
    evaluated_answers = len(valid_scores)

    return InterviewResultsResponse(
        interview_id=interview.id,
        status=interview.status,
        total_questions=total_questions,
        submitted_answers=submitted_answers,
        evaluated_answers=evaluated_answers,
        average_score=(
            sum(valid_scores) / evaluated_answers if evaluated_answers else None
        ),
        remaining_questions=max(total_questions - submitted_answers, 0),
        ready_for_completion=(
            total_questions > 0
            and submitted_answers == total_questions
            and evaluated_answers == total_questions
        )
    )


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
        logger.warning("Question generation provider failure: %s", type(e).__name__)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service is currently unavailable. Please try again later."
        )

    except AIResponseError as e:
        logger.warning("Question generation response failure: %s", type(e).__name__)

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
            logger.warning("Generated question validation failure: %s", type(e).__name__)

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

    except SQLAlchemyError as e:
        db.rollback()

        logger.error("Question persistence failed: %s", type(e).__name__)

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


#submit an answer to a question - only one answer allowed per question
@router.post(
    "/{interview_id}/questions/{question_id}/answer",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED
)
def create_answer(
    interview_id: int,
    question_id: int,
    answer_in: AnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(interview_id, db, current_user, lock=True)
    if interview.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed interview answers cannot be modified"
        )
    question = _get_owned_question(interview, question_id, db)

    existing_answer = (
        db.query(Answer)
        .filter(Answer.question_id == question.id)
        .first()
    )

    if existing_answer is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An answer has already been submitted for this question"
        )

    answer = Answer(
        question_id=question.id,
        interview_id=interview.id,
        answer_text=answer_in.answer_text
    )

    db.add(answer)

    try:
        db.commit()
        db.refresh(answer)

    # safety net for a race where two requests pass the existing_answer check together
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An answer has already been submitted for this question"
        )

    except SQLAlchemyError as e:
        db.rollback()

        logger.error("Answer creation failed: %s", type(e).__name__)

        raise HTTPException(
            status_code=500,
            detail="Failed to save answer"
        )

    return answer


#update the existing answer for a question - does not create a new row
@router.put(
    "/{interview_id}/questions/{question_id}/answer",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK
)
def update_answer(
    interview_id: int,
    question_id: int,
    answer_in: AnswerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(interview_id, db, current_user, lock=True)
    if interview.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed interview answers cannot be modified"
        )
    question = _get_owned_question(interview, question_id, db)

    answer = (
        db.query(Answer)
        .filter(Answer.question_id == question.id)
        .with_for_update()
        .populate_existing()
        .first()
    )

    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No answer has been submitted for this question yet"
        )

    answer.answer_text = answer_in.answer_text
    answer.answer_revision += 1
    answer.evaluation_token = None
    answer.evaluation_started_at = None

    # stale feedback no longer matches the edited answer text - delete it in the same transaction
    existing_feedback = (
        db.query(Feedback)
        .filter(Feedback.answer_id == answer.id)
        .first()
    )

    if existing_feedback is not None:
        db.delete(existing_feedback)

    try:
        db.commit()
        db.refresh(answer)

    except SQLAlchemyError as e:
        db.rollback()

        logger.error("Answer update failed: %s", type(e).__name__)

        raise HTTPException(
            status_code=500,
            detail="Failed to update answer"
        )

    return answer


#retrieve the saved answer for a single question
@router.get(
    "/{interview_id}/questions/{question_id}/answer",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK
)
def get_answer(
    interview_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(interview_id, db, current_user)
    question = _get_owned_question(interview, question_id, db)

    answer = (
        db.query(Answer)
        .filter(Answer.question_id == question.id)
        .first()
    )

    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found"
        )

    return answer


#retrieve every answered question for an interview, in question order
@router.get(
    "/{interview_id}/answers",
    response_model=list[InterviewAnswerResponse],
    status_code=status.HTTP_200_OK
)
def get_interview_answers(
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

    answers = []

    for question in questions:
        if question.answer is None:
            continue

        answers.append(
            InterviewAnswerResponse(
                id=question.answer.id,
                question_id=question.id,
                question_order=question.order_number,
                question_text=question.question_text,
                answer_text=question.answer.answer_text,
                created_at=question.answer.created_at
            )
        )

    return answers


#requests an AI evaluation of the answer already submitted for this question
@router.post(
    "/{interview_id}/questions/{question_id}/evaluate",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED
)
def evaluate_answer(
    interview_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(interview_id, db, current_user, lock=True)
    question = _get_owned_question(interview, question_id, db)
    answer = (
        db.query(Answer)
        .filter(Answer.question_id == question.id)
        .with_for_update()
        .populate_existing()
        .first()
    )

    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No answer has been submitted for this question yet"
        )

    existing_feedback = (
        db.query(Feedback)
        .filter(Feedback.answer_id == answer.id)
        .first()
    )

    if existing_feedback is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This answer has already been evaluated"
        )

    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(
        seconds=Evaluation_Reservation_Timeout_Seconds
    )
    started_at = answer.evaluation_started_at
    if started_at is not None and started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    if (
        answer.evaluation_token is not None
        and started_at is not None
        and started_at > stale_before
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An evaluation for this answer is already in progress"
        )

    token = str(uuid4())
    answer_id = answer.id
    answer_revision = answer.answer_revision
    answer_text = answer.answer_text
    evaluation_context = {
        "question_text": question.question_text,
        "question_type": question.question_type,
        "target_role": interview.target_role,
        "difficulty": question.difficulty,
        "job_description": interview.job_description,
    }
    cv = (
        db.query(CVDocument)
        .filter(CVDocument.id == interview.cv_id)
        .first()
    )
    evaluation_context["cv_text"] = cv.extracted_text if cv is not None else None

    reservation_result = (
        db.query(Answer)
        .filter(
            Answer.id == answer.id,
            Answer.answer_revision == answer_revision,
            or_(
                Answer.evaluation_token.is_(None),
                Answer.evaluation_started_at.is_(None),
                Answer.evaluation_started_at <= stale_before
            )
        )
        .update(
            {
                Answer.evaluation_token: token,
                Answer.evaluation_started_at: now
            },
            synchronize_session=False
        )
    )
    if reservation_result != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An evaluation for this answer is already in progress"
        )

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.error(
            "Evaluation reservation failed for answer %s: %s",
            answer_id,
            type(error).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reserve the answer for evaluation"
        ) from error

    logger.info(
        "Evaluation requested for answer %s (revision %s)",
        answer_id,
        answer_revision
    )

    try:
        result = ai_evaluate_answer(
            question_text=evaluation_context["question_text"],
            answer_text=answer_text,
            question_type=evaluation_context["question_type"],
            target_role=evaluation_context["target_role"],
            difficulty=evaluation_context["difficulty"],
            job_description=evaluation_context["job_description"],
            cv_text=evaluation_context["cv_text"]
        )

    except AIServiceError as e:
        logger.warning(
            "Evaluation provider failure for answer %s: %s",
            answer_id,
            type(e).__name__
        )
        _release_evaluation_reservation(db, answer_id, token)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service is currently unavailable. Please try again later."
        )

    except AIResponseError as e:
        logger.warning(
            "Evaluation response failure for answer %s: %s",
            answer_id,
            type(e).__name__
        )
        _release_evaluation_reservation(db, answer_id, token)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Received an invalid response while evaluating the answer."
        )

    # Re-lock both rows after the provider call: updates invalidate the token and
    # increment the revision before this result can be persisted.
    locked_interview = _get_owned_interview(
        interview_id, db, current_user, lock=True
    )
    if locked_interview.status == "completed":
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed interview answers cannot be evaluated"
        )
    current_answer = (
        db.query(Answer)
        .filter(Answer.id == answer_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if (
        current_answer is None
        or current_answer.evaluation_token != token
        or current_answer.answer_revision != answer_revision
    ):
        db.rollback()
        logger.info("Evaluation result became outdated for answer %s", answer_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The answer changed while it was being evaluated. Please retry."
        )

    feedback = Feedback(
        answer_id=current_answer.id,
        score=result["score"],
        strengths=result["strengths"],
        improvements=result["improvements"],
        feedback_text=result["feedback_text"],
        improved_answer=result["improved_answer"]
    )

    db.add(feedback)
    current_answer.evaluation_token = None
    current_answer.evaluation_started_at = None

    try:
        db.commit()
        db.refresh(feedback)

    # safety net for a race where two requests pass the existing_feedback check together
    except IntegrityError:
        db.rollback()
        _release_evaluation_reservation(db, answer_id, token)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This answer has already been evaluated"
        )

    except SQLAlchemyError as e:
        db.rollback()
        _release_evaluation_reservation(db, answer_id, token)

        logger.error(
            "Evaluation persistence failed for answer %s: %s",
            answer_id,
            type(e).__name__
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the evaluation"
        )

    logger.info("Evaluation completed for answer %s", answer_id)
    return feedback


#retrieve the stored evaluation for a question, together with the question and answer
@router.get(
    "/{interview_id}/questions/{question_id}/feedback",
    response_model=QuestionAnswerFeedbackResponse,
    status_code=status.HTTP_200_OK
)
def get_answer_feedback(
    interview_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(interview_id, db, current_user)
    question = _get_owned_question(interview, question_id, db)
    answer = _get_owned_answer(question, db)

    feedback = (
        db.query(Feedback)
        .filter(Feedback.answer_id == answer.id)
        .first()
    )

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    return QuestionAnswerFeedbackResponse(
        question=question,
        answer=answer,
        evaluation=feedback
    )


@router.post(
    "/{interview_id}/complete",
    response_model=InterviewResponse,
    status_code=status.HTTP_200_OK
)
def complete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    interview = _get_owned_interview(
        interview_id, db, current_user, lock=True
    )
    if interview.status == "completed":
        return interview

    rows = (
        db.query(InterviewQuestion, Answer, Feedback)
        .outerjoin(Answer, Answer.question_id == InterviewQuestion.id)
        .outerjoin(Feedback, Feedback.answer_id == Answer.id)
        .filter(InterviewQuestion.interview_id == interview.id)
        .all()
    )
    is_complete = (
        bool(rows)
        and all(answer is not None for _, answer, _ in rows)
        and all(
            feedback is not None and _valid_feedback(feedback)
            for _, _, feedback in rows
        )
    )
    if not is_complete:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Interview completion requires generated questions, an answer "
                "for every question, and valid feedback for every answer"
            )
        )

    interview.status = "completed"
    interview.completed_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(interview)
    except SQLAlchemyError as error:
        db.rollback()
        logger.error(
            "Interview completion failed for interview %s: %s",
            interview_id,
            type(error).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete the interview"
        ) from error

    logger.info("Interview %s completed", interview_id)
    return interview
