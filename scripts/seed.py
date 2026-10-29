"""Демо-данные через API: профиль компании, HR-аккаунт, вакансия, отклики (PDF) и демо-кандидат.
Запуск: python3 scripts/seed.py [--api http://localhost:8000]
Только стандартная библиотека. Повторный запуск ничего не дублирует.

Демо-аккаунты (только для локального запуска!):
  HR:       hr@koz.demo        / koz-demo-2026
  Кандидат: candidate@koz.demo / koz-demo-2026
"""

import argparse
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
DEMO_PASSWORD = "koz-demo-2026"

COMPANY = {
    "name": "KOZ AI",
    "tagline": "Делаем AI-решения, которые бизнес использует каждый день",
    "about": (
        "KOZ AI — IT-компания из Алматы. Мы разрабатываем SaaS-платформы, корпоративные системы, AI-агентов и инструменты "
        "автоматизации бизнес-процессов. Работаем по полному циклу: от изучения задачи заказчика и архитектуры до запуска в production."
    ),
    "highlights": [
        {"title": "Реальные проекты", "text": "Работаем с корпоративными клиентами и доводим решения до реального использования."},
        {"title": "Полный цикл", "text": "Участвуете во всём: от идеи и прототипа до production и сопровождения."},
        {"title": "Современный стек", "text": "LLM, AI-агенты, RAG, интеграции с ERP, CRM и 1С."},
    ],
    "location": "Алматы",
    "website": "",
    "contact_email": "",
}


def req(method: str, url: str, body: bytes | None = None, headers: dict | None = None, ctype: str = "application/json"):
    h = {"Content-Type": ctype, **(headers or {})}
    r = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def account(api: str, email: str, name: str, role: str, invite: str = "") -> str:
    code, data = req("POST", f"{api}/api/auth/login", json.dumps({"email": email, "password": DEMO_PASSWORD}).encode())
    if code == 200:
        return data["token"]
    code, data = req(
        "POST", f"{api}/api/auth/register",
        json.dumps({"email": email, "password": DEMO_PASSWORD, "full_name": name, "role": role, "invite_code": invite}).encode(),
    )
    if code != 200:
        raise SystemExit(f"Не удалось создать {email}: {data}")
    return data["token"]


def multipart(fields: dict, files: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    out = b""
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for field, name, data, mime in files:
        out += f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + data + b"\r\n"
    return out + f"--{b}--\r\n".encode(), f"multipart/form-data; boundary={b}"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--invite", default=os.environ.get("HR_INVITE_CODE", "koz-hr-2026"))
    a = p.parse_args()

    hr = {"Authorization": "Bearer " + account(a.api, "hr@koz.demo", "Айгуль Сапарова", "hr", a.invite)}
    code, vacancies = req("GET", f"{a.api}/api/vacancies", headers=hr)
    if vacancies:
        print("Демо-данные уже загружены — пропускаю.")
        return

    req("PUT", f"{a.api}/api/company", json.dumps(COMPANY).encode(), hr)
    text = (DATA / "vacancy_koz_ai_fullstack.txt").read_text(encoding="utf-8")
    code, draft = req("POST", f"{a.api}/api/vacancies/parse", json.dumps({"text": text}).encode(), hr)
    if code != 200:
        raise SystemExit(f"Разбор вакансии не удался: {draft}")
    code, v = req("POST", f"{a.api}/api/vacancies", json.dumps({**draft, "description": text, "status": "open"}).encode(), hr)
    print(f"Вакансия #{v['id']} «{v['title']}»: {len(v['requirements'])} требований")

    pdfs = sorted((DATA / "resumes_pdf").glob("*.pdf"))
    site = [x for x in pdfs if x.name.startswith("06_")]
    hr_upload = [x for x in pdfs if not x.name.startswith("06_")]
    body, ctype = multipart({}, [("files", x.name, x.read_bytes(), "application/pdf") for x in hr_upload])
    req("POST", f"{a.api}/api/vacancies/{v['id']}/candidates", body, hr, ctype)

    cand = {"Authorization": "Bearer " + account(a.api, "candidate@koz.demo", "Мадина Жаксылык", "candidate")}
    for x in site:
        body, ctype = multipart(
            {"cover_letter": "Здравствуйте! Последние два года делаю AI-функции в HR SaaS и хочу расти в Forward Deployed Engineering. Буду рада обсудить."},
            [("file", x.name, x.read_bytes(), "application/pdf")],
        )
        req("POST", f"{a.api}/api/jobs/{v['id']}/apply", body, cand, ctype)
    print(f"Резюме: {len(hr_upload)} загрузил HR, {len(site)} — отклик с сайта.")
    print(f"Вход HR: hr@koz.demo / {DEMO_PASSWORD}   Вход кандидата: candidate@koz.demo / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
