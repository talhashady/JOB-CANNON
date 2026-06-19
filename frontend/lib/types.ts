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
}

export interface SkillGapReport {
  missing_skills: string[];
  roadmap: { skill: string; resource: string }[] | string[];
}

export interface InterviewPrep {
  questions: string[];
}

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  platform: string;
  status: string;
  notes?: string[];
  created_at?: string;
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
  agent_chain: { agent: string; note: string; [k: string]: unknown }[];
  elapsed_s: number;
}

export interface RunParams {
  user_id: string;
  query: string;
  location: string;
  sites: string[];
  results_wanted: number;
  is_remote: boolean;
  top_k: number;
  auto_apply: boolean;
}
