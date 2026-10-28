"""Pydantic-схемы. ScreeningResult — это structured output, который мы требуем от LLM."""

from typing import Literal

from pydantic import BaseModel, Field


class Requirement(BaseModel):
    id: str
    text: str
    kind: Literal["must", "nice"] = "must"
    category: str = "general"


class RequirementList(BaseModel):
    requirements: list[Requirement]


class RequirementMatch(BaseModel):
    requirement_id: str
    status: Literal["met", "partial", "missing"]
    evidence: str = Field(default="", description="Цитата из резюме, подтверждающая оценку")
    comment: str = ""


class ScreeningResult(BaseModel):
    candidate_name: str = ""
    seniority: Literal["intern", "junior", "middle", "senior", "lead", "unknown"] = "unknown"
    years_of_experience: float | None = None
    matches: list[RequirementMatch]
    strengths: list[str] = []
    risks: list[str] = []
    interview_questions: list[str] = []
    summary: str = ""


# ---------- API ----------


class VacancyCreate(BaseModel):
    title: str
    company: str = ""
    description: str
    requirements: list[Requirement] | None = None  # если не задано — извлекаем LLM


class VacancyOut(BaseModel):
    id: int
    title: str
    company: str
    description: str
    requirements: list[Requirement]
    candidates_count: int = 0


class CandidateOut(BaseModel):
    id: int
    vacancy_id: int
    name: str
    filename: str
    status: str
    error: str = ""
    crm_id: str = ""
    score: float | None = None
    verdict: str | None = None
    # статус по каждому требованию в порядке вакансии: met | partial | missing
    fingerprint: list[str] = []


class CandidateDetail(CandidateOut):
    masked_text: str
    screening: dict | None = None
    usage: dict | None = None


class AgentMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentRequest(BaseModel):
    vacancy_id: int
    messages: list[AgentMessage]


class AgentResponse(BaseModel):
    answer: str
    tool_calls: list[dict] = []
