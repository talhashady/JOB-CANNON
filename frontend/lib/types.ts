// Mirrors the backend pydantic models (subset used by the UI).

export interface Job {
  id: string;
  source: string;
  title: string;
  company: string;
  location?: string;
  description?: string;
  url?: string;
  is_remote?: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  posted_at?: string | null;
  verified?: boolean;
}

export interface MatchResult {
  score: number;
  rationale: string;
  matched_skills: string[];
  missing_skills: string[];
  breakdown?: Record<string, number>;
}

export interface GeneratedResume {
  plain_text: string;
  highlights?: string[];
}

export interface GeneratedCoverLetter {
  body: string;
  subject?: string;
}

export interface SkillGapReport {
  missing_skills: string[];
  roadmap: { skill: string; resource: string }[] | string[];
}

export interface InterviewPrep {
  questions: string[];
}

// --- auth -------------------------------------------------------------------
export interface PublicUser {
  id: string;
  email: string;
  full_name?: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type?: string;
  user: PublicUser;
}

// --- profile ----------------------------------------------------------------
export interface UserProfile {
  user_id: string;
  full_name?: string;
  email?: string | null;
  headline?: string;
  summary?: string;
  skills: string[];
  years_experience: number;
  titles: string[];
  locations_preferred?: string[];
  remote_ok?: boolean;
  career_goals?: string;
  raw_cv_text?: string;
}

// --- applications -----------------------------------------------------------
export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  platform: string;
  status: string;
  job_title?: string;
  company?: string;
  job_url?: string;
  match_score?: number;
  apply_method?: string;
  apply_email?: string;
  notes?: string[];
  created_at?: string;
  updated_at?: string;
}

export interface Recommendation {
  job: Job;
  match: MatchResult;
  resume: GeneratedResume;
  cover_letter: GeneratedCoverLetter;
  application: Application | null;
  skill_gap: SkillGapReport;
  interview_prep: InterviewPrep;
}

export interface PipelineResult {
  user_id: string;
  query: string;
  jobs_scraped: number;
  jobs_verified: number;
  recommendations: Recommendation[];
  agent_chain: { agent: string; summary?: string; note?: string; [k: string]: unknown }[];
  elapsed_s: number;
}

// --- requests ---------------------------------------------------------------
export interface RunParams {
  query: string;
  location: string;
  sites: string[];
  results_wanted: number;
  is_remote: boolean;
  top_k: number;
  auto_apply: boolean;
}

export interface AutoApplyParams {
  query: string;
  location: string;
  sites: string[];
  results_wanted: number;
  is_remote: boolean;
  min_score?: number;
  max_applications?: number;
}

export interface AutoApplyResult {
  attempted: number;
  email_sent: number;
  dry_run: number;
  no_contact: number;
  applications: Application[];
}

export interface HealthResponse {
  status: string;
  llm_enabled: boolean;
  live_apply: boolean;
  smtp_configured?: boolean;
  default_sites?: string[];
}
