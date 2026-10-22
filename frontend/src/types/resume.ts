export interface ResumeExperience {
  company: string;
  role: string;
  start_date: string | null;
  end_date: string | null;
  description: string;
}

export interface ResumeEducation {
  school: string;
  department: string;
  start_date: string | null;
  end_date: string | null;
  gpa: string | null;
}

export interface ResumeProject {
  name: string;
  description: string;
  technologies: string[];
  link: string | null;
}

export interface ResumeLanguage {
  language: string;
  level: string | null;
}

export interface ResumeContent {
  personal_info: { name: string | null; email: string | null; phone: string | null };
  summary?: string | null;
  education: ResumeEducation[];
  experience: ResumeExperience[];
  projects: ResumeProject[];
  skills: string[];
  certificates: string[];
  languages: ResumeLanguage[];
}

export interface ChangeLogEntry {
  section: string;
  before: string;
  after: string;
  reason: string;
}

export type EditLevel = "light" | "targeted" | "from_scratch" | "manual";

export interface EditorVersion {
  id: number;
  version_number: number;
  edit_level: EditLevel;
  content: ResumeContent;
  change_log: ChangeLogEntry[];
  created_at: string;
}
