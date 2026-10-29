import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agent import run_agent
from app.auth import Principal, create_token, current_user, hash_password, optional_user, require_candidate, require_hr, verify_password
from app.config import get_settings
from app.db import get_db, init_db
from app.knowledge import find_skills
from app.llm import DEFAULT_MODELS, LLMError, get_provider
from app.models import Candidate, CompanyProfile, IntegrationLog, Screening, User, Vacancy
from app.parsing import UnsupportedFile
from app.schemas import (
    AgentRequest,
    AuthOut,
    CandidateDetail,
    CandidateOut,
    CompanyIn,
    CompanyOut,
    LoginIn,
    MyApplication,
    ParseRequest,
    PublicJob,
    RegisterIn,
    StageIn,
    UserOut,
    VacancyCreate,
    VacancyDraft,
    VacancyOut,
)
from app.screening import ingest_resume, parse_vacancy
from app.tasks import enqueue_screening
from app.tools import export_candidate

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------- helpers ----------


def _vacancy(db: Session, vid: int) -> Vacancy:
    v = db.get(Vacancy, vid)
    if not v:
        raise HTTPException(404, "Вакансия не найдена")
    return v


def _candidate(db: Session, cid: int) -> Candidate:
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(404, "Кандидат не найден")
    return c


def _company(db: Session) -> CompanyProfile:
    c = db.query(CompanyProfile).first()
    if c is None:
        c = CompanyProfile(name="Компания", tagline="", about="", highlights=[])
        db.add(c)
        db.commit()
    return c


def _vacancy_out(v: Vacancy, total: int = 0, new: int = 0) -> VacancyOut:
    return VacancyOut(
        id=v.id, title=v.title, company=v.company, description=v.description, requirements=v.requirements, summary=v.summary,
        responsibilities=v.responsibilities or [], conditions=v.conditions or [], location=v.location, employment=v.employment,
        salary=v.salary, status=v.status, candidates_count=total, new_count=new,
    )


def _public_job(v: Vacancy) -> PublicJob:
    return PublicJob(
        id=v.id, title=v.title, company=v.company, summary=v.summary, responsibilities=v.responsibilities or [],
        must=[r["text"] for r in v.requirements if r.get("kind") == "must"], nice=[r["text"] for r in v.requirements if r.get("kind") == "nice"],
        conditions=v.conditions or [], location=v.location, employment=v.employment, salary=v.salary, status=v.status,
    )


def _cand_out(c: Candidate, s: Screening | None, requirements: list[dict] | None = None) -> CandidateOut:
    fingerprint: list[str] = []
    if s and requirements:
        by_id = {m["requirement_id"]: m["status"] for m in s.result.get("matches", [])}
        fingerprint = [by_id.get(r["id"], "missing") for r in requirements]
    return CandidateOut(
        id=c.id, vacancy_id=c.vacancy_id, name=c.name, filename=c.filename, status=c.status, error=c.error,
        crm_id=c.crm_id, score=s.score if s else None, verdict=s.verdict if s else None, fingerprint=fingerprint,
        stage=c.stage, source=c.source, created_at=str(c.created_at or ""),
    )


def _user_out(p: Principal) -> UserOut:
    return UserOut(id=p.id, email=p.email, full_name=p.full_name, role=p.role)


# ---------- служебное ----------


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_provider": settings.llm_provider, "embedding_provider": settings.embedding_provider}


@app.get("/api/providers", dependencies=[Depends(require_hr)])
def providers():
    available = {
        "mock": True,
        "anthropic": bool(settings.anthropic_api_key),
        "openai": bool(settings.openai_api_key),
        "gemini": bool(settings.google_api_key),
        "ollama": True,
    }
    return [
        {"name": n, "default_model": (settings.llm_model if n == settings.llm_provider and settings.llm_model else DEFAULT_MODELS[n]), "configured": ok, "is_default": n == settings.llm_provider}
        for n, ok in available.items()
    ]


# ---------- авторизация ----------


@app.post("/api/auth/register", response_model=AuthOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if body.role == "hr" and (not settings.hr_invite_code or body.invite_code.strip() != settings.hr_invite_code):
        raise HTTPException(403, "Для HR-аккаунта нужен код приглашения от администратора")
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "Этот email уже зарегистрирован. Войдите или восстановите доступ")
    u = User(email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password), role=body.role)
    db.add(u)
    db.commit()
    return AuthOut(token=create_token(u), user=UserOut(id=u.id, email=u.email, full_name=u.full_name, role=u.role))


@app.post("/api/auth/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=body.email.strip().lower()).first()
    if u is None or not verify_password(body.password, u.password_hash) or not u.is_active:
        raise HTTPException(401, "Неверный email или пароль")
    return AuthOut(token=create_token(u), user=UserOut(id=u.id, email=u.email, full_name=u.full_name, role=u.role))


@app.get("/api/auth/me", response_model=UserOut)
def me(p: Principal = Depends(current_user)):
    return _user_out(p)


# ---------- публичная часть ----------


@app.get("/api/company", response_model=CompanyOut)
def company(db: Session = Depends(get_db)):
    c = _company(db)
    n = db.query(Vacancy).filter_by(status="open").count()
    return CompanyOut(name=c.name, tagline=c.tagline, about=c.about, highlights=c.highlights or [], location=c.location, website=c.website, contact_email=c.contact_email, open_jobs=n)


@app.put("/api/company", response_model=CompanyOut, dependencies=[Depends(require_hr)])
def update_company(body: CompanyIn, db: Session = Depends(get_db)):
    c = _company(db)
    for k, val in body.model_dump().items():
        setattr(c, k, val)
    db.commit()
    return company(db)


@app.get("/api/jobs", response_model=list[PublicJob])
def jobs(db: Session = Depends(get_db)):
    return [_public_job(v) for v in db.query(Vacancy).filter_by(status="open").order_by(Vacancy.id.desc())]


@app.get("/api/jobs/{vid}", response_model=PublicJob)
def job(vid: int, p: Principal | None = Depends(optional_user), db: Session = Depends(get_db)):
    v = _vacancy(db, vid)
    if v.status == "draft" and not (p and p.is_hr):
        raise HTTPException(404, "Вакансия не найдена")
    return _public_job(v)


# ---------- кандидат ----------


@app.post("/api/jobs/{vid}/apply", response_model=MyApplication)
async def apply(
    vid: int,
    file: UploadFile = File(...),
    cover_letter: str = Form(""),
    p: Principal = Depends(require_candidate),
    db: Session = Depends(get_db),
):
    v = _vacancy(db, vid)
    if v.status != "open":
        raise HTTPException(409, "Приём откликов на эту вакансию закрыт")
    if db.query(Candidate).filter_by(vacancy_id=vid, user_id=p.id).first():
        raise HTTPException(409, "Вы уже откликнулись на эту вакансию — статус виден в личном кабинете")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ")
    try:
        cand = ingest_resume(
            db, v, file.filename or "resume.pdf", data, user_id=p.id, source="site", cover_letter=cover_letter, name=p.full_name, email=p.email
        )
    except UnsupportedFile as e:
        raise HTTPException(422, str(e)) from e
    enqueue_screening(cand.id)
    return MyApplication(id=cand.id, vacancy_id=v.id, vacancy_title=v.title, filename=cand.filename, stage=cand.stage, created_at=str(cand.created_at or ""))


@app.get("/api/me/applications", response_model=list[MyApplication])
def my_applications(p: Principal = Depends(current_user), db: Session = Depends(get_db)):
    """Кандидат видит свои отклики и этап. Оценки ИИ кандидату не показываем."""
    rows = db.query(Candidate, Vacancy).join(Vacancy, Vacancy.id == Candidate.vacancy_id).filter(Candidate.user_id == p.id).order_by(Candidate.id.desc())
    return [MyApplication(id=c.id, vacancy_id=v.id, vacancy_title=v.title, filename=c.filename, stage=c.stage, created_at=str(c.created_at or "")) for c, v in rows]


@app.delete("/api/me/applications/{cid}")
def withdraw(cid: int, p: Principal = Depends(current_user), db: Session = Depends(get_db)):
    c = _candidate(db, cid)
    if c.user_id != p.id:
        raise HTTPException(404, "Отклик не найден")
    db.delete(c)
    db.commit()
    return {"deleted": cid}


@app.get("/api/applications/{cid}/file")
def application_file(cid: int, p: Principal = Depends(current_user), db: Session = Depends(get_db)):
    c = _candidate(db, cid)
    if not (p.is_hr or (p.id is not None and c.user_id == p.id)):
        raise HTTPException(404, "Файл не найден")
    data = db.query(Candidate.file_bytes).filter_by(id=cid).scalar()
    if data:
        return Response(data, media_type=c.file_mime or "application/octet-stream", headers={"Content-Disposition": f'inline; filename="resume-{cid}"'})
    return Response(c.raw_text.encode(), media_type="text/plain; charset=utf-8")


# ---------- HR: вакансии ----------


@app.post("/api/vacancies/parse", response_model=VacancyDraft, dependencies=[Depends(require_hr)])
def parse(body: ParseRequest, provider: str | None = None):
    try:
        return parse_vacancy(body.text, get_provider(provider))
    except LLMError as e:
        raise HTTPException(502, f"Модель не ответила: {e}") from e


def _fill_from_text(body: VacancyCreate) -> VacancyCreate:
    """Если HR прислал только текст — достраиваем структуру ИИ (обратная совместимость со старым API)."""
    if body.requirements is not None or not body.description.strip():
        return body
    try:
        d = parse_vacancy(body.description)
    except LLMError as e:
        raise HTTPException(502, f"Модель не ответила: {e}") from e
    return body.model_copy(
        update={
            "title": body.title or d.title,
            "summary": body.summary or d.summary,
            "responsibilities": body.responsibilities if body.responsibilities is not None else d.responsibilities,
            "requirements": d.requirements,
            "conditions": body.conditions if body.conditions is not None else d.conditions,
            "location": body.location or d.location,
            "employment": body.employment or d.employment,
            "salary": body.salary or d.salary,
        }
    )


@app.post("/api/vacancies", response_model=VacancyOut, dependencies=[Depends(require_hr)])
def create_vacancy(body: VacancyCreate, db: Session = Depends(get_db)):
    body = _fill_from_text(body)
    if not body.title.strip():
        raise HTTPException(422, "Укажите название должности")
    reqs = [r.model_dump() for r in (body.requirements or [])]
    for i, r in enumerate(reqs, 1):
        r["id"] = r.get("id") or f"r{i}"
    if body.status == "open" and not reqs:
        raise HTTPException(422, "Чтобы опубликовать вакансию, нужны требования — по ним ИИ оценивает кандидатов")
    v = Vacancy(
        title=body.title.strip(), company=body.company or _company(db).name, description=body.description, requirements=reqs,
        summary=body.summary, responsibilities=body.responsibilities or [], conditions=body.conditions or [], location=body.location,
        employment=body.employment, salary=body.salary, status=body.status,
    )
    db.add(v)
    db.commit()
    return _vacancy_out(v)


def _counts(db: Session) -> tuple[dict, dict]:
    total = dict(db.query(Candidate.vacancy_id, func.count()).group_by(Candidate.vacancy_id).all())
    new = dict(db.query(Candidate.vacancy_id, func.count()).filter(Candidate.stage == "new").group_by(Candidate.vacancy_id).all())
    return total, new


@app.get("/api/vacancies", response_model=list[VacancyOut], dependencies=[Depends(require_hr)])
def list_vacancies(db: Session = Depends(get_db)):
    total, new = _counts(db)
    return [_vacancy_out(v, total.get(v.id, 0), new.get(v.id, 0)) for v in db.query(Vacancy).order_by(Vacancy.id.desc())]


@app.get("/api/vacancies/{vid}", response_model=VacancyOut, dependencies=[Depends(require_hr)])
def get_vacancy(vid: int, db: Session = Depends(get_db)):
    total, new = _counts(db)
    return _vacancy_out(_vacancy(db, vid), total.get(vid, 0), new.get(vid, 0))


@app.put("/api/vacancies/{vid}", response_model=VacancyOut, dependencies=[Depends(require_hr)])
def update_vacancy(vid: int, body: VacancyCreate, db: Session = Depends(get_db)):
    v = _vacancy(db, vid)
    reqs = [r.model_dump() for r in (body.requirements or [])] if body.requirements is not None else v.requirements
    for i, r in enumerate(reqs, 1):
        r["id"] = r.get("id") or f"r{i}"
    v.title = body.title or v.title
    v.summary, v.location, v.employment, v.salary, v.status = body.summary, body.location, body.employment, body.salary, body.status
    v.requirements = reqs
    if body.responsibilities is not None:
        v.responsibilities = body.responsibilities
    if body.conditions is not None:
        v.conditions = body.conditions
    if body.description:
        v.description = body.description
    db.commit()
    return get_vacancy(vid, db)


@app.put("/api/vacancies/{vid}/requirements", response_model=VacancyOut, dependencies=[Depends(require_hr)])
def update_requirements(vid: int, reqs: list[dict], db: Session = Depends(get_db)):
    v = _vacancy(db, vid)
    v.requirements = reqs
    db.commit()
    return _vacancy_out(v)


# ---------- HR: кандидаты ----------


@app.post("/api/vacancies/{vid}/candidates", response_model=list[CandidateOut], dependencies=[Depends(require_hr)])
async def upload_resumes(
    vid: int,
    files: list[UploadFile] = File(...),
    provider: str | None = Query(None),
    model: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """HR загружает резюме сам (например, из почты или hh.ru)."""
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


@app.get("/api/vacancies/{vid}/candidates", response_model=list[CandidateOut], dependencies=[Depends(require_hr)])
def ranking(vid: int, db: Session = Depends(get_db)):
    v = _vacancy(db, vid)
    rows = db.query(Candidate, Screening).outerjoin(Screening, Screening.candidate_id == Candidate.id).filter(Candidate.vacancy_id == vid).all()
    rows.sort(key=lambda x: (x[1].score if x[1] else -1), reverse=True)
    return [_cand_out(c, s, v.requirements) for c, s in rows]


@app.get("/api/candidates/{cid}", response_model=CandidateDetail, dependencies=[Depends(require_hr)])
def candidate_detail(cid: int, db: Session = Depends(get_db)):
    c = _candidate(db, cid)
    s = db.query(Screening).filter_by(candidate_id=cid).first()
    v = db.get(Vacancy, c.vacancy_id)
    base = _cand_out(c, s, v.requirements if v else None).model_dump()
    usage = (
        {"provider": s.provider, "model": s.model, "input_tokens": s.input_tokens, "output_tokens": s.output_tokens, "cost_usd": s.cost_usd, "latency_ms": s.latency_ms}
        if s else None
    )
    has_file = db.query(Candidate.file_bytes.isnot(None)).filter_by(id=cid).scalar()
    return CandidateDetail(
        **base, masked_text=c.masked_text, screening=s.result if s else None, usage=usage, cover_letter=c.cover_letter,
        email=(c.contacts.get("emails") or [""])[0], phone=(c.contacts.get("phones") or [""])[0], has_file=bool(has_file), file_mime=c.file_mime,
    )


@app.patch("/api/candidates/{cid}/stage", response_model=CandidateOut, dependencies=[Depends(require_hr)])
def set_stage(cid: int, body: StageIn, db: Session = Depends(get_db)):
    c = _candidate(db, cid)
    c.stage = body.stage
    db.commit()
    return _cand_out(c, db.query(Screening).filter_by(candidate_id=cid).first())


@app.post("/api/candidates/{cid}/rescreen", dependencies=[Depends(require_hr)])
def rescreen(cid: int, provider: str | None = None, model: str | None = None, db: Session = Depends(get_db)):
    _candidate(db, cid)
    enqueue_screening(cid, provider, model)
    return {"queued": True}


@app.post("/api/candidates/{cid}/export", dependencies=[Depends(require_hr)])
def export(cid: int, system: str = "bitrix24", db: Session = Depends(get_db)):
    c = _candidate(db, cid)
    try:
        return export_candidate(db, c.vacancy_id, cid, system)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Ошибка интеграции: {e}") from e


@app.delete("/api/candidates/{cid}", dependencies=[Depends(require_hr)])
def delete_candidate(cid: int, db: Session = Depends(get_db)):
    """Удаление по запросу кандидата (право на удаление ПДн)."""
    db.delete(_candidate(db, cid))
    db.commit()
    return {"deleted": cid}


# ---------- HR: ассистент и аналитика ----------


@app.post("/api/agent/chat", dependencies=[Depends(require_hr)])
def agent_chat(body: AgentRequest, provider: str | None = None, db: Session = Depends(get_db)):
    _vacancy(db, body.vacancy_id)
    try:
        return run_agent(db, body.vacancy_id, [m.model_dump() for m in body.messages], get_provider(provider))
    except LLMError as e:
        raise HTTPException(502, str(e)) from e


@app.get("/api/vacancies/{vid}/analytics", dependencies=[Depends(require_hr)])
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
    stages: dict[str, int] = {}
    for c in cands:
        stages[c.stage] = stages.get(c.stage, 0) + 1
    skills: dict[str, int] = {}
    for c in cands:
        for sk in find_skills(c.masked_text):
            skills[sk] = skills.get(sk, 0) + 1
    n = len(screenings) or 1
    return {
        "candidates": len(cands),
        "screened": len(screenings),
        "verdicts": verdicts,
        "stages": stages,
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


@app.get("/api/integrations/logs", dependencies=[Depends(require_hr)])
def integration_logs(db: Session = Depends(get_db)):
    logs = db.query(IntegrationLog).order_by(IntegrationLog.id.desc()).limit(50).all()
    return [{"id": x.id, "system": x.system, "action": x.action, "candidate_id": x.candidate_id, "status": x.status, "request": x.request, "created_at": str(x.created_at)} for x in logs]
