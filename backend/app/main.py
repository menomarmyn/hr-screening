import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agent import run_agent
from app.config import get_settings
from app.db import get_db, init_db
from app.knowledge import find_skills
from app.llm import DEFAULT_MODELS, LLMError
from app.models import Candidate, IntegrationLog, Screening, Vacancy
from app.parsing import UnsupportedFile
from app.schemas import AgentRequest, CandidateDetail, CandidateOut, VacancyCreate, VacancyOut
from app.screening import extract_requirements, ingest_resume
from app.tasks import enqueue_screening
from app.tools import export_candidate

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def require_key(x_api_key: str = Header(default="")):
    if x_api_key != settings.api_key:
        raise HTTPException(401, "Неверный X-API-Key")


def _vacancy(db: Session, vid: int) -> Vacancy:
    v = db.get(Vacancy, vid)
    if not v:
        raise HTTPException(404, "Вакансия не найдена")
    return v


def _cand_out(c: Candidate, s: Screening | None) -> CandidateOut:
    return CandidateOut(
        id=c.id, vacancy_id=c.vacancy_id, name=c.name, filename=c.filename, status=c.status, error=c.error,
        crm_id=c.crm_id, score=s.score if s else None, verdict=s.verdict if s else None,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_provider": settings.llm_provider, "embedding_provider": settings.embedding_provider}


@app.get("/api/providers", dependencies=[Depends(require_key)])
def providers():
    available = {
        "mock": True,
        "anthropic": bool(settings.anthropic_api_key),
        "openai": bool(settings.openai_api_key),
        "gemini": bool(settings.google_api_key),
        "ollama": True,
    }
    return [{"name": n, "default_model": DEFAULT_MODELS[n], "configured": ok} for n, ok in available.items()]


# ---------- Вакансии ----------


@app.post("/api/vacancies", response_model=VacancyOut, dependencies=[Depends(require_key)])
def create_vacancy(body: VacancyCreate, db: Session = Depends(get_db)):
    try:
        reqs = [r.model_dump() for r in body.requirements] if body.requirements else extract_requirements(body.description)
    except LLMError as e:
        raise HTTPException(502, f"LLM: {e}") from e
    if not reqs:
        raise HTTPException(422, "Не удалось выделить требования из описания вакансии")
    v = Vacancy(title=body.title, company=body.company, description=body.description, requirements=reqs)
    db.add(v)
    db.commit()
    return VacancyOut(id=v.id, title=v.title, company=v.company, description=v.description, requirements=v.requirements)


@app.get("/api/vacancies", response_model=list[VacancyOut], dependencies=[Depends(require_key)])
def list_vacancies(db: Session = Depends(get_db)):
    counts = dict(db.query(Candidate.vacancy_id, func.count()).group_by(Candidate.vacancy_id).all())
    return [
        VacancyOut(id=v.id, title=v.title, company=v.company, description=v.description, requirements=v.requirements, candidates_count=counts.get(v.id, 0))
        for v in db.query(Vacancy).order_by(Vacancy.id.desc())
    ]


@app.put("/api/vacancies/{vid}/requirements", response_model=VacancyOut, dependencies=[Depends(require_key)])
def update_requirements(vid: int, reqs: list[dict], db: Session = Depends(get_db)):
    """HR может поправить требования, которые извлекла модель (human-in-the-loop)."""
    v = _vacancy(db, vid)
    v.requirements = reqs
    db.commit()
    return VacancyOut(id=v.id, title=v.title, company=v.company, description=v.description, requirements=v.requirements)


# ---------- Кандидаты ----------


@app.post("/api/vacancies/{vid}/candidates", response_model=list[CandidateOut], dependencies=[Depends(require_key)])
async def upload_resumes(
    vid: int,
    files: list[UploadFile] = File(...),
    provider: str | None = Query(None),
    model: str | None = Query(None),
    db: Session = Depends(get_db),
):
    v = _vacancy(db, vid)
    out = []
    for f in files:
        data = await f.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"{f.filename}: файл больше {settings.max_upload_mb} МБ")
        try:
            cand = ingest_resume(db, v, f.filename or "resume.txt", data)
        except UnsupportedFile as e:
            raise HTTPException(422, f"{f.filename}: {e}") from e
        out.append(cand.id)
    for cid in out:
        enqueue_screening(cid, provider, model)
    db.expire_all()
    return [_cand_out(db.get(Candidate, cid), db.query(Screening).filter_by(candidate_id=cid).first()) for cid in out]


@app.get("/api/vacancies/{vid}/candidates", response_model=list[CandidateOut], dependencies=[Depends(require_key)])
def ranking(vid: int, db: Session = Depends(get_db)):
    _vacancy(db, vid)
    rows = db.query(Candidate, Screening).outerjoin(Screening, Screening.candidate_id == Candidate.id).filter(Candidate.vacancy_id == vid).all()
    rows.sort(key=lambda x: (x[1].score if x[1] else -1), reverse=True)
    return [_cand_out(c, s) for c, s in rows]


@app.get("/api/candidates/{cid}", response_model=CandidateDetail, dependencies=[Depends(require_key)])
def candidate_detail(cid: int, db: Session = Depends(get_db)):
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(404, "Кандидат не найден")
    s = db.query(Screening).filter_by(candidate_id=cid).first()
    base = _cand_out(c, s).model_dump()
    usage = (
        {"provider": s.provider, "model": s.model, "input_tokens": s.input_tokens, "output_tokens": s.output_tokens, "cost_usd": s.cost_usd, "latency_ms": s.latency_ms}
        if s else None
    )
    return CandidateDetail(**base, masked_text=c.masked_text, screening=s.result if s else None, usage=usage)


@app.post("/api/candidates/{cid}/rescreen", dependencies=[Depends(require_key)])
def rescreen(cid: int, provider: str | None = None, model: str | None = None, db: Session = Depends(get_db)):
    if not db.get(Candidate, cid):
        raise HTTPException(404, "Кандидат не найден")
    enqueue_screening(cid, provider, model)
    return {"queued": True}


@app.post("/api/candidates/{cid}/export", dependencies=[Depends(require_key)])
def export(cid: int, system: str = "bitrix24", db: Session = Depends(get_db)):
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(404, "Кандидат не найден")
    try:
        return export_candidate(db, c.vacancy_id, cid, system)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Ошибка интеграции: {e}") from e


@app.delete("/api/candidates/{cid}", dependencies=[Depends(require_key)])
def delete_candidate(cid: int, db: Session = Depends(get_db)):
    """Удаление по запросу кандидата (право на удаление ПДн)."""
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(404, "Кандидат не найден")
    db.delete(c)
    db.commit()
    return {"deleted": cid}


# ---------- Агент ----------


@app.post("/api/agent/chat", dependencies=[Depends(require_key)])
def agent_chat(body: AgentRequest, provider: str | None = None, db: Session = Depends(get_db)):
    from app.llm import get_provider

    _vacancy(db, body.vacancy_id)
    try:
        return run_agent(db, body.vacancy_id, [m.model_dump() for m in body.messages], get_provider(provider))
    except LLMError as e:
        raise HTTPException(502, str(e)) from e


# ---------- Аналитика ----------


@app.get("/api/vacancies/{vid}/analytics", dependencies=[Depends(require_key)])
def analytics(vid: int, db: Session = Depends(get_db)):
    v = _vacancy(db, vid)
    screenings = db.query(Screening).filter_by(vacancy_id=vid).all()
    cands = db.query(Candidate).filter_by(vacancy_id=vid).all()
    verdicts = {"strong": 0, "maybe": 0, "reject": 0}
    req_stats = {r["id"]: {"text": r["text"], "kind": r["kind"], "met": 0, "partial": 0, "missing": 0} for r in v.requirements}
    for s in screenings:
        verdicts[s.verdict] = verdicts.get(s.verdict, 0) + 1
        for m in s.result.get("matches", []):
            if m["requirement_id"] in req_stats:
                req_stats[m["requirement_id"]][m["status"]] += 1
    skills: dict[str, int] = {}
    for c in cands:
        for sk in find_skills(c.masked_text):
            skills[sk] = skills.get(sk, 0) + 1
    n = len(screenings) or 1
    return {
        "candidates": len(cands),
        "screened": len(screenings),
        "verdicts": verdicts,
        "avg_score": round(sum(s.score for s in screenings) / n, 1) if screenings else None,
        "requirements": list(req_stats.values()),
        "top_skills": sorted(skills.items(), key=lambda x: -x[1])[:15],
        "cost": {
            "total_usd": round(sum(s.cost_usd for s in screenings), 4),
            "per_resume_usd": round(sum(s.cost_usd for s in screenings) / n, 5),
            "avg_latency_ms": int(sum(s.latency_ms for s in screenings) / n),
            "tokens": sum(s.input_tokens + s.output_tokens for s in screenings),
            "by_model": _by_model(screenings),
        },
    }


def _by_model(screenings: list[Screening]) -> list[dict]:
    agg: dict[str, dict] = {}
    for s in screenings:
        a = agg.setdefault(f"{s.provider}/{s.model}", {"model": f"{s.provider}/{s.model}", "count": 0, "cost_usd": 0.0, "latency_ms": 0})
        a["count"] += 1
        a["cost_usd"] += s.cost_usd
        a["latency_ms"] += s.latency_ms
    for a in agg.values():
        a["avg_latency_ms"] = int(a.pop("latency_ms") / a["count"])
        a["cost_usd"] = round(a["cost_usd"], 5)
    return list(agg.values())


@app.get("/api/integrations/logs", dependencies=[Depends(require_key)])
def integration_logs(db: Session = Depends(get_db)):
    logs = db.query(IntegrationLog).order_by(IntegrationLog.id.desc()).limit(50).all()
    return [{"id": x.id, "system": x.system, "action": x.action, "candidate_id": x.candidate_id, "status": x.status, "request": x.request, "created_at": str(x.created_at)} for x in logs]
