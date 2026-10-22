export type QuestionSource = "general" | "cv_specific" | "job_specific";
export type SessionType = "hr" | "technical" | "behavioral";

export interface AnswerFeedback {
  too_general: boolean;
  missing_technical_detail: boolean;
  missing_position_connection: boolean;
  structure_notes: string;
}

export interface AnswerEvaluation {
  question_id: number;
  question: string;
  user_answer: string;
  feedback: AnswerFeedback;
  suggested_improved_answer: string;
  follow_up_question: string | null;
  next_question_id: number | null;
  remaining_questions: number;
}

export interface InterviewQuestion {
  id: number;
  order_index: number;
  question: string;
  category: string | null;
  source: QuestionSource | null;
  star_applicable: boolean;
  answer: string | null;
  evaluation?: {
    feedback: AnswerFeedback;
    suggested_improved_answer: string;
    follow_up_question: string | null;
  } | null;
}

export const FEEDBACK_LABELS: Record<keyof Omit<AnswerFeedback, "structure_notes">, string> = {
  too_general: "Fazla genel",
  missing_technical_detail: "Teknik detay eksik",
  missing_position_connection: "Pozisyonla bağ kurulmamış",
};

export interface InterviewSession {
  id: number;
  session_type: string;
  status: string;
  resume_id: number | null;
  resume_version_id: number | null;
  job_posting_id: number | null;
  questions: InterviewQuestion[];
  created_at: string;
}

export const SOURCE_LABELS: Record<QuestionSource, string> = {
  general: "Genel",
  cv_specific: "CV'ye özel",
  job_specific: "İlana özel",
};

export const SESSION_TYPE_LABELS: Record<string, string> = {
  hr: "İK Görüşmesi",
  technical: "Teknik Görüşme",
  behavioral: "Davranışsal Görüşme",
};
