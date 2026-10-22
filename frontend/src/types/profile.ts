export type WorkModePreference = "remote" | "hybrid" | "office";

export interface Profile {
  id: number;
  user_id: number;
  education_level: string | null;
  department: string | null;
  university: string | null;
  graduation_year: number | null;
  work_experience: string[] | null;
  internship_experience: string[] | null;
  technical_skills: string[] | null;
  certificates: string[] | null;
  projects: string[] | null;
  english_level: string | null;
  target_city: string | null;
  work_mode_preference: WorkModePreference | null;
  career_goal: string | null;
  created_at: string;
  updated_at: string;
}

export type ProfileFormData = Omit<
  Profile,
  "id" | "user_id" | "created_at" | "updated_at"
>;

export const EMPTY_PROFILE_FORM: ProfileFormData = {
  education_level: "",
  department: "",
  university: "",
  graduation_year: null,
  work_experience: [],
  internship_experience: [],
  technical_skills: [],
  certificates: [],
  projects: [],
  english_level: "",
  target_city: "",
  work_mode_preference: null,
  career_goal: "",
};
