from datetime import datetime

from pydantic import Field

from app.agents.interview_schema import QuestionSource, SessionType
from app.schemas.base import APISchema, ORMSchema


class InterviewQuestionsRequest(APISchema):
    session_type: SessionType
    resume_version_id: int | None = None
    resume_id: int | None = None
    job_posting_id: int | None = None


class InterviewQuestionResponse(ORMSchema):
    id: int
    order_index: int
    question: str
    category: str | None
    source: QuestionSource | None
    star_applicable: bool
    answer: str | None
    evaluation: dict | None = None


class InterviewSessionResponse(ORMSchema):
    id: int
    session_type: str
    status: str
    resume_id: int | None
    resume_version_id: int | None
    job_posting_id: int | None
    questions: list[InterviewQuestionResponse]
    created_at: datetime


class InterviewAnswerUpdate(APISchema):
    """Kullanıcının STAR notu / cevabı."""

    answer: str | None = None


# --- Simülasyon: cevap değerlendirme ---


class AnswerSubmission(APISchema):
    question_id: int
    user_answer: str = Field(min_length=1, max_length=10000)


class AnswerFeedbackSchema(APISchema):
    too_general: bool
    missing_technical_detail: bool
    missing_position_connection: bool
    structure_notes: str


class AnswerEvaluationResponse(APISchema):
    question_id: int
    question: str
    user_answer: str
    feedback: AnswerFeedbackSchema
    suggested_improved_answer: str
    follow_up_question: str | None
    next_question_id: int | None
    remaining_questions: int
