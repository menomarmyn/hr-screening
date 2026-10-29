from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.config import get_settings
from app.db import Base

DIM = get_settings().embedding_dim


class EmbeddingType(TypeDecorator):
    """pgvector в PostgreSQL, JSON-массив в SQLite (для тестов без БД)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(DIM))
        return dialect.type_descriptor(JSON())

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return [float(x) for x in value]


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text)
    # [{"id": "r1", "text": "...", "kind": "must"|"nice", "category": "..."}]
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    # Публичная карточка вакансии (собирается ИИ из свободного текста, HR правит)
    summary: Mapped[str] = mapped_column(Text, default="")
    responsibilities: Mapped[list] = mapped_column(JSON, default=list)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    location: Mapped[str] = mapped_column(String(255), default="")
    employment: Mapped[str] = mapped_column(String(255), default="")
    salary: Mapped[str] = mapped_column(String(255), default="")
    # draft — видна только HR, open — опубликована, closed — приём откликов закрыт
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    screenings: Mapped[list["Screening"]] = relationship(back_populates="vacancy", cascade="all, delete")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    filename: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)
    masked_text: Mapped[str] = mapped_column(Text)  # то, что уходит в LLM
    contacts: Mapped[dict] = mapped_column(JSON, default=dict)  # хранится только у нас
    # uploaded -> processing -> screened | failed
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    error: Mapped[str] = mapped_column(Text, default="")
    crm_id: Mapped[str] = mapped_column(String(64), default="")
    # Отклик с сайта: кто подал, сопроводительное, этап отбора, оригинал файла
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(16), default="upload")  # upload — загрузил HR, site — отклик с сайта
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    # new -> review -> interview -> offer | rejected
    stage: Mapped[str] = mapped_column(String(16), default="new")
    file_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    file_mime: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chunks: Mapped[list["ResumeChunk"]] = relationship(back_populates="candidate", cascade="all, delete")
    screenings: Mapped[list["Screening"]] = relationship(back_populates="candidate", cascade="all, delete")


class ResumeChunk(Base):
    __tablename__ = "resume_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(EmbeddingType)

    candidate: Mapped[Candidate] = relationship(back_populates="chunks")


class Screening(Base):
    __tablename__ = "screenings"

    id: Mapped[int] = mapped_column(primary_key=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float)
    verdict: Mapped[str] = mapped_column(String(16))
    result: Mapped[dict] = mapped_column(JSON)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vacancy: Mapped[Vacancy] = relationship(back_populates="screenings")
    candidate: Mapped[Candidate] = relationship(back_populates="screenings")


class IntegrationLog(Base):
    """Журнал обращений к внешним системам (CRM, 1С) — для аудита и отладки внедрения."""

    __tablename__ = "integration_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    system: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request: Mapped[dict] = mapped_column(JSON)
    response: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16))  # ok | dry_run | error
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))  # candidate | hr
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CompanyProfile(Base):
    """Публичная страница компании. Одна запись, редактирует HR."""

    __tablename__ = "company_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    tagline: Mapped[str] = mapped_column(String(500), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    # [{"title": "...", "text": "..."}]
    highlights: Mapped[list] = mapped_column(JSON, default=list)
    location: Mapped[str] = mapped_column(String(255), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="")
