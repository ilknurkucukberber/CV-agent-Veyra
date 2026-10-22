export interface JobRequirements {
  required_skills: string[];
  preferred_skills: string[];
  experience_years: string | null;
  programming_languages: string[];
  tools_and_technologies: string[];
  education_requirement: string | null;
  language_requirement: string | null;
  key_responsibilities: string[];
}

export interface JobPosting {
  id: number;
  title: string;
  company: string | null;
  location: string | null;
  url: string | null;
  requirements: JobRequirements | null;
  created_at: string;
}

export interface ImprovementSuggestion {
  suggestion: string;
  reason: string;
}

export interface JobMatch {
  id: number;
  job_posting_id: number;
  resume_id: number;
  resume_version_id: number | null;
  match_percentage: number;
  matched_skills: string[];
  missing_skills: string[];
  improvement_suggestions: ImprovementSuggestion[];
  created_at: string;
}
