export interface ExperienceDescription {
  role: string;
  linkedin_version: string;
}

export interface ChecklistItem {
  item: string;
  present: boolean | null;
}

export interface LinkedInOptimizeResult {
  headline_options: string[];
  about_section: string;
  experience_descriptions: ExperienceDescription[];
  suggested_skills: string[];
  profile_completeness_checklist: ChecklistItem[];
  headline_max_length: number;
}
