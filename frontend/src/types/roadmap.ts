export interface DevelopmentStep {
  step: number;
  action: string;
  estimated_effort: string;
}

export interface CareerRoadmap {
  id: number;
  target_role: string;
  resume_id: number | null;
  resume_version_id: number | null;
  job_posting_id: number | null;
  current_strengths: string[];
  gaps: string[];
  development_plan: DevelopmentStep[];
  completed_steps: number[];
  progress_percentage: number;
  created_at: string;
  updated_at: string;
}
