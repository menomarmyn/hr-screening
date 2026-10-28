"""Инструменты, доступные AI-агенту (function calling) и внешним клиентам через MCP-сервер.
Одна реализация — два способа вызова."""

from sqlalchemy.orm import Session

from app import rag
from app.integrations import EXPORTERS
from app.llm import ToolSpec
from app.models import Candidate, Screening, Vacancy


def _row(c: Candidate, s: Screening | None) -> dict:
    return {"id": c.id, "name": c.name, "filename": c.filename, "score": s.score if s else None, "verdict": s.verdict if s else None, "status": c.status}


def _screening(db: Session, cid: int) -> Screening | None:
    return db.query(Screening).filter(Screening.candidate_id == cid).first()


def _check(db: Session, vacancy_id: int, candidate_id: int) -> Candidate:
    c = db.get(Candidate, candidate_id)
    if c is None or c.vacancy_id != vacancy_id:
        raise ValueError(f"Кандидат #{candidate_id} не найден в этой вакансии")
    return c


def vacancy_requirements(db: Session, vacancy_id: int) -> dict:
    v = db.get(Vacancy, vacancy_id)
    return {"title": v.title, "requirements": v.requirements}


def rank_candidates(db: Session, vacancy_id: int, limit: int = 5, verdict: str | None = None) -> list[dict]:
    q = db.query(Candidate, Screening).outerjoin(Screening, Screening.candidate_id == Candidate.id).filter(Candidate.vacancy_id == vacancy_id)
    if verdict:
        q = q.filter(Screening.verdict == verdict)
    rows = sorted(q.all(), key=lambda x: (x[1].score if x[1] else -1), reverse=True)
    return [_row(c, s) for c, s in rows[: max(1, min(limit, 50))]]


def search_candidates(db: Session, vacancy_id: int, query: str, limit: int = 5) -> list[dict]:
    out = []
    for hit in rag.search_candidates(db, vacancy_id, query, limit):
        c = db.get(Candidate, hit["candidate_id"])
        out.append({**_row(c, _screening(db, c.id)), "similarity": hit["similarity"], "snippet": hit["snippet"]})
    return out


def get_candidate(db: Session, vacancy_id: int, candidate_id: int) -> dict:
    c = _check(db, vacancy_id, candidate_id)
    s = _screening(db, c.id)
    return {**_row(c, s), "screening": s.result if s else None, "resume_excerpt": c.masked_text[:1500]}


def compare_candidates(db: Session, vacancy_id: int, candidate_ids: list[int]) -> list[dict]:
    v = db.get(Vacancy, vacancy_id)
    req_text = {r["id"]: r["text"] for r in v.requirements}
    out = []
    for cid in candidate_ids[:5]:
        c = _check(db, vacancy_id, cid)
        s = _screening(db, c.id)
        matrix = {req_text.get(m["requirement_id"], m["requirement_id"])[:60]: m["status"] for m in (s.result["matches"] if s else [])}
        out.append({**_row(c, s), "matrix": matrix})
    return out


def export_candidate(db: Session, vacancy_id: int, candidate_id: int, system: str = "bitrix24") -> dict:
    c = _check(db, vacancy_id, candidate_id)
    if system not in EXPORTERS:
        raise ValueError(f"Система {system} не поддерживается. Доступно: {', '.join(EXPORTERS)}")
    return EXPORTERS[system](db, c)


TOOLS = {
    "vacancy_requirements": vacancy_requirements,
    "rank_candidates": rank_candidates,
    "search_candidates": search_candidates,
    "get_candidate": get_candidate,
    "compare_candidates": compare_candidates,
    "export_candidate": export_candidate,
}

TOOL_SPECS = [
    ToolSpec("vacancy_requirements", "Список требований текущей вакансии.", {"type": "object", "properties": {}}),
    ToolSpec(
        "rank_candidates",
        "Рейтинг кандидатов по баллу AI-скрининга. Можно отфильтровать по вердикту.",
        {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 5}, "verdict": {"type": "string", "enum": ["strong", "maybe", "reject"]}},
        },
    ),
    ToolSpec(
        "search_candidates",
        "Семантический поиск по резюме (RAG). Используй для вопросов вида 'у кого был опыт с X'.",
        {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}}, "required": ["query"]},
    ),
    ToolSpec(
        "get_candidate",
        "Подробности по кандидату: результат скрининга, сильные стороны, риски, вопросы, фрагмент резюме.",
        {"type": "object", "properties": {"candidate_id": {"type": "integer"}}, "required": ["candidate_id"]},
    ),
    ToolSpec(
        "compare_candidates",
        "Сравнить 2-5 кандидатов по матрице требований.",
        {"type": "object", "properties": {"candidate_ids": {"type": "array", "items": {"type": "integer"}}}, "required": ["candidate_ids"]},
    ),
    ToolSpec(
        "export_candidate",
        "Выгрузить кандидата в CRM (bitrix24) или 1С. Действие меняет внешнюю систему — вызывай только по явной просьбе пользователя.",
        {
            "type": "object",
            "properties": {"candidate_id": {"type": "integer"}, "system": {"type": "string", "enum": ["bitrix24", "1c"]}},
            "required": ["candidate_id"],
        },
    ),
]


def call_tool(db: Session, vacancy_id: int, name: str, args: dict):
    if name not in TOOLS:
        raise ValueError(f"Неизвестный инструмент {name}")
    return TOOLS[name](db, vacancy_id, **args)
