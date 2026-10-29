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


class VacancyDraft(BaseModel):
    """То, что ИИ собирает из свободного текста HR: публичная карточка + проверяемые требования."""

    title: str = Field(description="Название должности")
    summary: str = Field(default="", description="2-3 предложения для кандидата: чем предстоит заниматься и почему это интересно")
    responsibilities: list[str] = Field(default=[], description="Обязанности, каждая — короткая фраза")
    requirements: list[Requirement] = Field(default=[], description="Проверяемые требования к кандидату")
    conditions: list[str] = Field(default=[], description="Что предлагает компания")
    location: str = ""
    employment: str = Field(default="", description="Формат: офис, гибрид, удалёнка, полная занятость и т.п.")
    salary: str = Field(default="", description="Зарплата, если указана; иначе пусто")


class ExperienceItem(BaseModel):
    company: str = ""
    role: str = ""
    period: str = ""
    highlights: list[str] = []


class ResumeProfile(BaseModel):
    """Резюме, «раскрытое» ИИ в структуру."""

    headline: str = Field(default="", description="Кто это в одной строке, например «Python-разработчик, 4 года, финтех»")
    experience: list[ExperienceItem] = []
    skills: list[str] = []
    education: list[str] = []
    languages: list[str] = []


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
    profile: ResumeProfile = ResumeProfile()


# ---------- API ----------


class VacancyCreate(BaseModel):
    """Создание/правка вакансии HR. Если пришёл только description (свободный текст) — разбираем ИИ."""

    title: str = ""
    company: str = ""
    description: str = ""
    summary: str = ""
    responsibilities: list[str] | None = None
    requirements: list[Requirement] | None = None
    conditions: list[str] | None = None
    location: str = ""
    employment: str = ""
    salary: str = ""
    status: Literal["draft", "open", "closed"] = "open"


class VacancyOut(BaseModel):
    id: int
    title: str
    company: str
    description: str
    requirements: list[Requirement]
    summary: str = ""
    responsibilities: list[str] = []
    conditions: list[str] = []
    location: str = ""
    employment: str = ""
    salary: str = ""
    status: str = "open"
    candidates_count: int = 0
    new_count: int = 0


class PublicJob(BaseModel):
    id: int
    title: str
    company: str
    summary: str
    responsibilities: list[str]
    must: list[str]
    nice: list[str]
    conditions: list[str]
    location: str
    employment: str
    salary: str
    status: str


class ParseRequest(BaseModel):
    text: str = Field(min_length=20, description="Текст вакансии в любом виде")


class CompanyIn(BaseModel):
    name: str
    tagline: str = ""
    about: str = ""
    highlights: list[dict] = []
    location: str = ""
    website: str = ""
    contact_email: str = ""


class CompanyOut(CompanyIn):
    open_jobs: int = 0


class RegisterIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    role: Literal["candidate", "hr"] = "candidate"
    invite_code: str = ""


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int | None
    email: str
    full_name: str
    role: str


class AuthOut(BaseModel):
    token: str
    user: UserOut


class MyApplication(BaseModel):
    id: int
    vacancy_id: int
    vacancy_title: str
    filename: str
    stage: str
    created_at: str


class StageIn(BaseModel):
    stage: Literal["new", "review", "interview", "offer", "rejected"]


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
    stage: str = "new"
    source: str = "upload"
    created_at: str = ""
    # статус по каждому требованию в порядке вакансии: met | partial | missing
    fingerprint: list[str] = []


class CandidateDetail(CandidateOut):
    masked_text: str
    cover_letter: str = ""
    email: str = ""
    phone: str = ""
    has_file: bool = False
    file_mime: str = ""
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
