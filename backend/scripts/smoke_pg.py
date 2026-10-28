"""Smoke-тест на реальном PostgreSQL + pgvector: индексация, векторный поиск, скрининг.
Запуск: DATABASE_URL=postgresql+psycopg://... python -m scripts.smoke_pg"""

from pathlib import Path

from app.db import SessionLocal, init_db, is_postgres
from app.models import Vacancy
from app.rag import search_chunks
from app.screening import extract_requirements, ingest_resume, screen_candidate

DATA = Path(__file__).resolve().parents[2] / "data"


def main() -> None:
    assert is_postgres(), "Нужен DATABASE_URL на PostgreSQL"
    init_db()
    db = SessionLocal()
    desc = (DATA / "vacancy_koz_ai_fullstack.txt").read_text()
    v = Vacancy(title="smoke", company="KOZ AI", description=desc, requirements=extract_requirements(desc))
    db.add(v)
    db.commit()
    path = DATA / "resumes" / "01_arman_sadykov.txt"
    cand = ingest_resume(db, v, path.name, path.read_bytes())
    hits = search_chunks(db, "локальные LLM vLLM закрытый контур", candidate_id=cand.id, k=2)
    assert hits, "pgvector-поиск ничего не вернул"
    scr = screen_candidate(db, cand.id)
    print(f"ok: {len(hits)} hits, score={scr.score}, verdict={scr.verdict}")
    db.delete(v)
    db.commit()


if __name__ == "__main__":
    main()
