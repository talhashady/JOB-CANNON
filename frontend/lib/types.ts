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
  date_posted?: string | null;
  verified?: boolean;
}

export interface MatchResult {
  job_id?: string;
  score: number;
  skill_score?: number;
  experience_score?: number;
  location_score?: number;
  goal_score?: number;
  rationale: string;
  matched_skills: string[];
  missing_skills: string[];
}

export interface GeneratedResume {
  job_id?: string;
  summary?: string;
  plain_text: string;
  highlighted_skills?: string[];
  sections?: string[];
  ats_passed?: boolean;
  ats_issues?: string[];
}

export interface GeneratedCoverLetter {
  job_id?: string;
  body: string;
  subject?: string;
  word_count?: number;
}

export interface SkillGapReport {
  job_id?: string;
  missing_skills: string[];
  learning_roadmap: string[];
  estimated_weeks?: number;
}

export interface InterviewPrep {
  job_id?: string;
  technical_questions: string[];
  behavioral_questions: string[];
  tips?: string[];
}

// --- auth -------------------------------------------------------------------
export interface PublicUser {
  id: string;
  email: string;
  full_name?: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token?: string;
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
  data_source?: string;
  is_demo?: boolean;
  scrape_warning?: string | null;
  jobs_scraped: number;
  jobs_verified: number;
  recommendations: Recommendation[];
  failed_recommendations?: { job_title: string; company: string; url?: string; reason: string }[];
  agent_chain: { agent: string; summary?: string; note?: string; [k: string]: unknown }[];
  elapsed_s: number;
}

// --- requests ---------------------------------------------------------------
export interface RunParams {
  query: string;
  location: string;
  country?: string;
  sites: string[];
  results_wanted: number;
  is_remote: boolean;
  work_arrangement: string; // any | remote | hybrid | onsite
  top_k: number;
  auto_apply: boolean;
  apply_min_score?: number;
  apply_min_skill_score?: number;
  confirm_live_apply?: boolean;
}

export interface AutoApplyParams {
  query: string;
  location: string;
  country?: string;
  sites: string[];
  results_wanted: number;
  is_remote: boolean;
  work_arrangement: string; // any | remote | hybrid | onsite
  min_score?: number;
  min_skill_score?: number;
  max_applications?: number;
  confirm_live_apply?: boolean;
}

export interface AutoApplyResult {
  user_id: string;
  query: string;
  data_source?: string;
  is_demo?: boolean;
  scrape_warning?: string | null;
  jobs_scraped: number;
  jobs_verified: number;
  min_score: number;
  min_skill_score?: number;
  max_applications: number;
  submitted_count: number;
  dry_run: boolean;
  daily_cap: number;
  applied: { job: Job; match: MatchResult; application: Application }[];
  skipped: { job: Job; reason: string }[];
  elapsed_s: number;
}


export interface DiscoveryMatch {
  job: Job;
  match: MatchResult;
}

export interface DiscoveryResult {
  user_id: string;
  query: string;
  data_source?: string;
  is_demo?: boolean;
  scrape_warning?: string | null;
  jobs_scraped: number;
  jobs_verified: number;
  matches: DiscoveryMatch[];
  agent_chain: { agent: string; summary?: string; note?: string; [k: string]: unknown }[];
  elapsed_s: number;
}

export interface PrepareParams {
  job_ids: string[];
  auto_apply: boolean;
  confirm_live_apply?: boolean;
}

export interface HealthResponse {
  status: string;
  llm_enabled: boolean;
  live_apply: boolean;
  smtp_configured?: boolean;
  default_sites?: string[];
}

