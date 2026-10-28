import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["CELERY_EAGER"] = "true"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["REDIS_URL"] = "redis://localhost:1/0"  # недоступен → кэш отключается
os.environ["API_KEY"] = "test-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        c.headers["X-API-Key"] = "test-key"
        yield c


@pytest.fixture(scope="session")
def vacancy(client):
    desc = (DATA / "vacancy_koz_ai_fullstack.txt").read_text(encoding="utf-8")
    r = client.post("/api/vacancies", json={"title": "Fullstack AI Engineer", "company": "KOZ AI", "description": desc})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def screened(client, vacancy):
    files = [("files", (p.name, p.read_bytes(), "text/plain")) for p in sorted((DATA / "resumes").glob("*.txt"))]
    r = client.post(f"/api/vacancies/{vacancy['id']}/candidates", files=files)
    assert r.status_code == 200, r.text
    return r.json()
