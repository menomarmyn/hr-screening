export type Kind = "must" | "nice";
export type Verdict = "strong" | "maybe" | "reject";
export type MatchStatus = "met" | "partial" | "missing";
export type Stage = "new" | "review" | "interview" | "offer" | "rejected";
export type Role = "candidate" | "hr";

export interface User {
  id: number | null;
  email: string;
  full_name: string;
  role: Role;
}

export interface Requirement {
  id: string;
  text: string;
  kind: Kind;
  category: string;
}

export interface Company {
  name: string;
  tagline: string;
  about: string;
  highlights: { title: string; text: string }[];
  location: string;
  website: string;
  contact_email: string;
  open_jobs: number;
}

export interface PublicJob {
  id: number;
  title: string;
  company: string;
  summary: string;
  responsibilities: string[];
  must: string[];
  nice: string[];
  conditions: string[];
  location: string;
  employment: string;
  salary: string;
  status: "draft" | "open" | "closed";
}

export interface VacancyDraft {
  title: string;
  summary: string;
  responsibilities: string[];
  requirements: Requirement[];
  conditions: string[];
  location: string;
  employment: string;
  salary: string;
}

export interface Vacancy extends VacancyDraft {
  id: number;
  company: string;
  description: string;
  status: "draft" | "open" | "closed";
  candidates_count: number;
  new_count: number;
}

export interface MyApplication {
  id: number;
  vacancy_id: number;
  vacancy_title: string;
  filename: string;
  stage: Stage;
  created_at: string;
}

export interface Candidate {
  id: number;
  vacancy_id: number;
  name: string;
  filename: string;
  status: "uploaded" | "processing" | "screened" | "failed";
  error: string;
  crm_id: string;
  score: number | null;
  verdict: Verdict | null;
  stage: Stage;
  source: "upload" | "site";
  created_at: string;
  fingerprint?: MatchStatus[];
}

export interface RequirementMatch {
  requirement_id: string;
  status: MatchStatus;
  evidence: string;
  comment: string;
}

export interface ResumeProfile {
  headline: string;
  experience: { company: string; role: string; period: string; highlights: string[] }[];
  skills: string[];
  education: string[];
  languages: string[];
}

export interface ScreeningResult {
  candidate_name: string;
  seniority: string;
  years_of_experience: number | null;
  matches: RequirementMatch[];
  strengths: string[];
  risks: string[];
  interview_questions: string[];
  summary: string;
  profile?: ResumeProfile;
}

export interface CandidateDetail extends Candidate {
  masked_text: string;
  screening: ScreeningResult | null;
  usage: { provider: string; model: string; input_tokens: number; output_tokens: number; cost_usd: number; latency_ms: number } | null;
  cover_letter: string;
  email: string;
  phone: string;
  has_file: boolean;
  file_mime: string;
}

export interface Provider {
  name: string;
  default_model: string;
  configured: boolean;
  is_default: boolean;
}

export interface ToolTrace {
  name: string;
  arguments: Record<string, unknown>;
  result_preview: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tools?: ToolTrace[];
}
