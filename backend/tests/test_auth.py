"""Роли и права: кандидат видит только своё, HR — всё, гость — только публичную часть."""

import io

import pytest
from fastapi.testclient import TestClient


def make_pdf(text: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in text.splitlines():
        c.drawString(40, y, line)
        y -= 16
    c.save()
    return buf.getvalue()


RESUME = """John Smith
Python developer, 5 years experience
2020 - 2025 Backend Developer, Acme Corp
- Built REST API with FastAPI and PostgreSQL, Docker, Git, Linux
- Integrated OpenAI API, RAG with embeddings and pgvector
Skills: Python, FastAPI, PostgreSQL, SQL, Docker, React, TypeScript
"""


@pytest.fixture(scope="module")
def anon(client):
    from app.main import app

    with TestClient(app) as c:
        yield c


def _register(c, email, role="candidate", code="", name="Тест Тестов"):
    return c.post("/api/auth/register", json={"email": email, "password": "password123", "full_name": name, "role": role, "invite_code": code})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def hr_token(anon):
    from app.config import get_settings

    r = _register(anon, "hr@test.kz", "hr", get_settings().hr_invite_code, "Айжан HR")
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def cand_token(anon):
    r = _register(anon, "cand@test.kz", name="Кандидат Первый")
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def other_token(anon):
    return _register(anon, "other@test.kz", name="Кандидат Второй").json()["token"]


@pytest.fixture(scope="module")
def open_job(anon, hr_token):
    text = "Ищем Python-разработчика в Алматы, гибрид. Будешь писать API на FastAPI. Нужен опыт с Python и PostgreSQL от 3 лет. Желательно знание 1С. Платим от 900 000 тенге."
    draft = anon.post("/api/vacancies/parse", json={"text": text}, headers=_auth(hr_token))
    assert draft.status_code == 200, draft.text
    d = draft.json()
    assert d["requirements"] and d["location"] == "Алматы"
    r = anon.post("/api/vacancies", json={**d, "status": "open"}, headers=_auth(hr_token))
    assert r.status_code == 200, r.text
    return r.json()


def test_hr_registration_requires_invite(anon):
    assert _register(anon, "fake-hr@test.kz", "hr", "wrong").status_code == 403


def test_duplicate_and_bad_login(anon, cand_token):
    assert _register(anon, "CAND@test.kz").status_code == 409
    assert anon.post("/api/auth/login", json={"email": "cand@test.kz", "password": "nope-nope"}).status_code == 401
    ok = anon.post("/api/auth/login", json={"email": "cand@test.kz", "password": "password123"})
    assert ok.status_code == 200 and ok.json()["user"]["role"] == "candidate"


def test_guest_sees_only_public(anon, open_job):
    assert anon.get("/api/jobs").status_code == 200
    assert anon.get("/api/company").status_code == 200
    assert anon.get("/api/vacancies").status_code == 401
    assert anon.post(f"/api/jobs/{open_job['id']}/apply", files={"file": ("cv.pdf", b"x", "application/pdf")}).status_code == 401


def test_candidate_cannot_use_hr_api(anon, cand_token, open_job):
    h = _auth(cand_token)
    assert anon.get("/api/vacancies", headers=h).status_code == 403
    assert anon.get(f"/api/vacancies/{open_job['id']}/candidates", headers=h).status_code == 403
    assert anon.put("/api/company", json={"name": "Hacked"}, headers=h).status_code == 403
    assert anon.post("/api/vacancies/parse", json={"text": "x" * 30}, headers=h).status_code == 403


def test_drafts_are_hidden(anon, hr_token):
    r = anon.post("/api/vacancies", json={"title": "Секретный черновик", "status": "draft"}, headers=_auth(hr_token))
    assert r.status_code == 200
    vid = r.json()["id"]
    assert all(j["id"] != vid for j in anon.get("/api/jobs").json())
    assert anon.get(f"/api/jobs/{vid}").status_code == 404
    assert anon.get(f"/api/jobs/{vid}", headers=_auth(hr_token)).status_code == 200


def test_apply_flow_and_privacy(anon, hr_token, cand_token, other_token, open_job):
    vid = open_job["id"]
    pdf = make_pdf(RESUME)
    r = anon.post(f"/api/jobs/{vid}/apply", data={"cover_letter": "Хочу к вам"}, files={"file": ("cv.pdf", pdf, "application/pdf")}, headers=_auth(cand_token))
    assert r.status_code == 200, r.text
    app_id = r.json()["id"]

    # повторный отклик запрещён
    again = anon.post(f"/api/jobs/{vid}/apply", files={"file": ("cv.pdf", pdf, "application/pdf")}, headers=_auth(cand_token))
    assert again.status_code == 409

    # кандидат видит свой отклик, но не оценку
    mine = anon.get("/api/me/applications", headers=_auth(cand_token)).json()
    assert [a["id"] for a in mine] == [app_id]
    assert "score" not in mine[0] and mine[0]["stage"] == "new"
    assert anon.get("/api/me/applications", headers=_auth(other_token)).json() == []

    # оригинал PDF: владелец и HR — да, чужой кандидат — нет
    own = anon.get(f"/api/applications/{app_id}/file", headers=_auth(cand_token))
    assert own.status_code == 200 and own.headers["content-type"] == "application/pdf" and own.content == pdf
    assert anon.get(f"/api/applications/{app_id}/file", headers=_auth(other_token)).status_code == 404
    assert anon.get(f"/api/applications/{app_id}/file", headers=_auth(hr_token)).status_code == 200

    # HR видит отклик с разбором ИИ и сопроводительным
    d = anon.get(f"/api/candidates/{app_id}", headers=_auth(hr_token)).json()
    assert d["source"] == "site" and d["cover_letter"] == "Хочу к вам" and d["has_file"]
    assert d["email"] == "cand@test.kz" and d["name"] == "Кандидат Первый"
    assert d["screening"]["profile"]["experience"], "ИИ должен раскрыть опыт из PDF"

    # HR меняет этап — кандидат видит новый этап
    assert anon.patch(f"/api/candidates/{app_id}/stage", json={"stage": "interview"}, headers=_auth(hr_token)).status_code == 200
    assert anon.get("/api/me/applications", headers=_auth(cand_token)).json()[0]["stage"] == "interview"

    # кандидат не может менять этап и не может удалить чужой отклик
    assert anon.patch(f"/api/candidates/{app_id}/stage", json={"stage": "offer"}, headers=_auth(cand_token)).status_code == 403
    assert anon.delete(f"/api/me/applications/{app_id}", headers=_auth(other_token)).status_code == 404


def test_closed_job_rejects_applications(anon, hr_token, other_token, open_job):
    body = {**open_job, "status": "closed"}
    assert anon.put(f"/api/vacancies/{open_job['id']}", json=body, headers=_auth(hr_token)).status_code == 200
    r = anon.post(f"/api/jobs/{open_job['id']}/apply", files={"file": ("cv.pdf", make_pdf(RESUME), "application/pdf")}, headers=_auth(other_token))
    assert r.status_code == 409


def test_bad_token(anon):
    assert anon.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
