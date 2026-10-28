export type Kind = "must" | "nice";
export type Verdict = "strong" | "maybe" | "reject";
export type MatchStatus = "met" | "partial" | "missing";

export interface Requirement {
  id: string;
  text: string;
  kind: Kind;
  category: string;
}

export interface Vacancy {
  id: number;
  title: string;
  company: string;
  description: string;
  requirements: Requirement[];
  candidates_count: number;
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
  fingerprint?: MatchStatus[];
}

export interface RequirementMatch {
  requirement_id: string;
  status: MatchStatus;
  evidence: string;
  comment: string;
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
}

export interface Usage {
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
}

export interface CandidateDetail extends Candidate {
  masked_text: string;
  screening: ScreeningResult | null;
  usage: Usage | null;
}

export interface Provider {
  name: string;
  default_model: string;
  configured: boolean;
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

export interface Analytics {
  candidates: number;
  screened: number;
  verdicts: Record<Verdict, number>;
  avg_score: number | null;
  requirements: { text: string; kind: Kind; met: number; partial: number; missing: number }[];
  top_skills: [string, number][];
  cost: {
    total_usd: number;
    per_resume_usd: number;
    avg_latency_ms: number;
    tokens: number;
    by_model: { model: string; count: number; cost_usd: number; avg_latency_ms: number }[];
  };
}
