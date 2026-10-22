export interface AtsGap {
  issue: string;
  why_it_matters: string;
  how_to_fix: string;
}

export type AtsCategoryKey =
  | "format_readability"
  | "contact_info"
  | "experience_quality"
  | "technical_skills"
  | "keyword_match"
  | "projects_achievements"
  | "language_quality";

export interface AtsAnalysis {
  id: number;
  resume_id: number;
  job_posting_id: number | null;
  total_score: number;
  category_scores: Record<AtsCategoryKey, number>;
  strengths: string[];
  gaps: AtsGap[];
  disclaimer: string;
  created_at: string;
}

export const CATEGORY_WEIGHTS: Record<AtsCategoryKey, number> = {
  format_readability: 15,
  contact_info: 10,
  experience_quality: 20,
  technical_skills: 15,
  keyword_match: 20,
  projects_achievements: 15,
  language_quality: 5,
};

export const CATEGORY_LABELS: Record<AtsCategoryKey, string> = {
  format_readability: "Biçim ve okunabilirlik",
  contact_info: "İletişim ve temel bilgiler",
  experience_quality: "Deneyim açıklamaları",
  technical_skills: "Teknik beceriler",
  keyword_match: "Anahtar kelime uyumu",
  projects_achievements: "Projeler ve başarılar",
  language_quality: "Dil ve yazım kalitesi",
};
