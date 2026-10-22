from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.interview_agent import InterviewAgentError, generate_questions
from app.agents.interview_evaluator import InterviewEvaluationError, evaluate_answer
from app.api.deps import CurrentUser, DbSession, Language
from app.models import (
    InterviewAnswer,
    InterviewSession,
    JobPosting,
    Resume,
    ResumeVersion,
)
from app.schemas.interview import (
    AnswerEvaluationResponse,
    AnswerFeedbackSchema,
    AnswerSubmission,
    InterviewAnswerUpdate,
    InterviewQuestionResponse,
    InterviewQuestionsRequest,
    InterviewSessionResponse,
)

router = APIRouter(prefix="/interview", tags=["interview"])


def _load_session(db: DbSession, user_id: int, session_id: int) -> InterviewSession:
    session = db.scalar(
        select(InterviewSession)
        .options(selectinload(InterviewSession.answers))
        .where(InterviewSession.id == session_id, InterviewSession.user_id == user_id)
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Görüşme oturumu bulunamadı"
        )
    return session


def _to_response(session: InterviewSession) -> InterviewSessionResponse:
    return InterviewSessionResponse(
        id=session.id,
        session_type=session.session_type,
        status=session.status,
        resume_id=session.resume_id,
        resume_version_id=session.resume_version_id,
        job_posting_id=session.job_posting_id,
        created_at=session.created_at,
        questions=[
            InterviewQuestionResponse.model_validate(answer) for answer in session.answers
        ],
    )


@router.post(
    "/questions",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_questions(
    payload: InterviewQuestionsRequest, current_user: CurrentUser, db: DbSession, language: Language
) -> InterviewSessionResponse:
    if payload.resume_version_id is not None:
        version = db.scalar(
            select(ResumeVersion)
            .join(Resume, Resume.id == ResumeVersion.resume_id)
            .where(
                ResumeVersion.id == payload.resume_version_id,
                Resume.user_id == current_user.id,
            )
        )
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="CV versiyonu bulunamadı"
            )
        resume = db.get(Resume, version.resume_id)
        content = version.content
    elif payload.resume_id is not None:
        resume = db.scalar(
            select(Resume).where(
                Resume.id == payload.resume_id, Resume.user_id == current_user.id
            )
        )
        if resume is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="CV bulunamadı"
            )
        version = None
        content = resume.parsed_json
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resume_version_id veya resume_id alanlarından biri zorunludur.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CV içeriği boş; önce CV'nin ayrıştırılmasını bekleyin.",
        )

    job_posting = None
    if payload.job_posting_id is not None:
        job_posting = db.scalar(
            select(JobPosting).where(
                JobPosting.id == payload.job_posting_id,
                JobPosting.user_id == current_user.id,
            )
        )
        if job_posting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="İş ilanı bulunamadı"
            )

    try:
        question_set = generate_questions(
            payload.session_type,
            content,
            job_title=job_posting.title if job_posting else None,
            job_requirements=job_posting.requirements if job_posting else None,
            language=language,
        )
    except InterviewAgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    session = InterviewSession(
        user_id=current_user.id,
        resume_id=resume.id if resume else None,
        resume_version_id=version.id if version else None,
        job_posting_id=payload.job_posting_id,
        session_type=payload.session_type.value,
        status="prepared",
    )
    for index, question in enumerate(question_set.questions):
        session.answers.append(
            InterviewAnswer(
                order_index=index,
                question=question.question,
                category=question.category,
                source=question.source.value,
                star_applicable=question.star_applicable,
            )
        )

    db.add(session)
    db.commit()
    db.refresh(session)
    return _to_response(session)


@router.get("/sessions", response_model=list[InterviewSessionResponse])
def list_sessions(current_user: CurrentUser, db: DbSession) -> list[InterviewSessionResponse]:
    sessions = db.scalars(
        select(InterviewSession)
        .options(selectinload(InterviewSession.answers))
        .where(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
    )
    return [_to_response(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=InterviewSessionResponse)
def get_session(
    session_id: int, current_user: CurrentUser, db: DbSession
) -> InterviewSessionResponse:
    return _to_response(_load_session(db, current_user.id, session_id))


@router.post(
    "/sessions/{session_id}/answer",
    response_model=AnswerEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_answer(
    session_id: int,
    payload: AnswerSubmission,
    current_user: CurrentUser,
    db: DbSession,
    language: Language,
) -> AnswerEvaluationResponse:
    session = _load_session(db, current_user.id, session_id)
    question = next((a for a in session.answers if a.id == payload.question_id), None)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Soru bu oturumda bulunamadı",
        )

    job_title = session.job_posting.title if session.job_posting else None

    try:
        evaluation = evaluate_answer(
            question.question,
            payload.user_answer,
            question.star_applicable,
            session.session_type,
            job_title,
            job_requirements=session.job_posting.requirements if session.job_posting else None,
            language=language,
        )
    except InterviewEvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    question.answer = payload.user_answer
    question.evaluation = evaluation.model_dump()
    question.feedback = evaluation.feedback.structure_notes
    question.answered_at = datetime.now(timezone.utc)

    remaining = [a for a in session.answers if a.id != question.id and not a.answer]
    remaining.sort(key=lambda a: a.order_index)
    session.status = "in_progress" if remaining else "completed"
    if not remaining:
        session.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(question)

    return AnswerEvaluationResponse(
        question_id=question.id,
        question=question.question,
        user_answer=payload.user_answer,
        feedback=AnswerFeedbackSchema(**evaluation.feedback.model_dump()),
        suggested_improved_answer=evaluation.suggested_improved_answer,
        follow_up_question=evaluation.follow_up_question,
        next_question_id=remaining[0].id if remaining else None,
        remaining_questions=len(remaining),
    )


@router.patch(
    "/sessions/{session_id}/questions/{question_id}",
    response_model=InterviewQuestionResponse,
)
def update_answer(
    session_id: int,
    question_id: int,
    payload: InterviewAnswerUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> InterviewAnswer:
    session = _load_session(db, current_user.id, session_id)
    question = next((a for a in session.answers if a.id == question_id), None)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Soru bulunamadı"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)
    db.commit()
    db.refresh(question)
    return question
