"""RAG по резюме: чанкинг, эмбеддинги в pgvector, поиск фрагментов-доказательств."""

from sqlalchemy import Float, bindparam, select
from sqlalchemy.orm import Session

from app.db import is_postgres
from app.embeddings import cosine, embed
from app.models import Candidate, ResumeChunk
from app.parsing import chunk_text


def index_candidate(db: Session, candidate: Candidate) -> int:
    db.query(ResumeChunk).filter(ResumeChunk.candidate_id == candidate.id).delete()
    chunks = chunk_text(candidate.masked_text)
    vectors = embed(chunks)
    for i, (text, vec) in enumerate(zip(chunks, vectors)):
        db.add(ResumeChunk(candidate_id=candidate.id, position=i, text=text, embedding=vec))
    db.flush()
    return len(chunks)


def search_chunks(
    db: Session, query: str, *, candidate_id: int | None = None, vacancy_id: int | None = None, k: int = 3
) -> list[tuple[ResumeChunk, float]]:
    qvec = embed([query])[0]
    stmt = select(ResumeChunk).join(Candidate)
    if candidate_id is not None:
        stmt = stmt.where(ResumeChunk.candidate_id == candidate_id)
    if vacancy_id is not None:
        stmt = stmt.where(Candidate.vacancy_id == vacancy_id)

    if is_postgres():
        from pgvector.sqlalchemy import Vector

        # <=> — косинусное расстояние pgvector, ускоряется HNSW-индексом (см. db.init_db)
        dist = ResumeChunk.embedding.op("<=>", return_type=Float)(bindparam("q", qvec, type_=Vector(len(qvec))))
        rows = db.execute(stmt.add_columns(dist.label("d")).order_by(dist).limit(k)).all()
        return [(row[0], 1 - float(row[1])) for row in rows]

    # SQLite (тесты): считаем косинус в Python
    chunks = db.scalars(stmt).all()
    scored = sorted(((c, cosine(qvec, c.embedding)) for c in chunks), key=lambda x: x[1], reverse=True)
    return scored[:k]


def search_candidates(db: Session, vacancy_id: int, query: str, limit: int = 5) -> list[dict]:
    """Семантический поиск кандидатов: лучший фрагмент на кандидата."""
    hits = search_chunks(db, query, vacancy_id=vacancy_id, k=limit * 5)
    best: dict[int, tuple[ResumeChunk, float]] = {}
    for chunk, sim in hits:
        if chunk.candidate_id not in best or sim > best[chunk.candidate_id][1]:
            best[chunk.candidate_id] = (chunk, sim)
    ranked = sorted(best.values(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"candidate_id": c.candidate_id, "similarity": round(s, 3), "snippet": c.text[:200]} for c, s in ranked]
