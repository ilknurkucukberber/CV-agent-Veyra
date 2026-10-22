export type ApplicationStatus = 
  | 'saved'
  | 'applied'
  | 'hr_interview'
  | 'technical_interview'
  | 'offer'
  | 'rejected'
  | 'awaiting_response';

export interface Application {
  id: number;
  user_id: number;
  company: string;
  position: string;
  job_posting_id?: number;
  resume_version_id?: number;
  status: ApplicationStatus;
  applied_at?: string;
  interview_at?: string;
  notes?: string;
  interview_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreate {
  company: string;
  position: string;
  job_posting_id?: number;
  resume_version_id?: number;
  status?: ApplicationStatus;
  interview_at?: string;
  notes?: string;
  interview_notes?: string;
}

export interface ApplicationUpdate {
  company?: string;
  position?: string;
  job_posting_id?: number;
  resume_version_id?: number;
  status?: ApplicationStatus;
  interview_at?: string | null;
  notes?: string;
  interview_notes?: string;
}
