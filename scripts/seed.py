"""Загружает демо-данные через API: вакансию KOZ AI и резюме из data/resumes.
Запуск: python3 scripts/seed.py [--api http://localhost:8000] [--provider mock]
Работает на стандартной библиотеке, ставить ничего не нужно."""

import argparse
import json
import os
import uuid
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def call(url: str, key: str, body: bytes, content_type: str) -> dict:
    req = urllib.request.Request(url, data=body, method="POST", headers={"X-API-Key": key, "Content-Type": content_type})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--provider", default="")
    p.add_argument("--key", default=os.environ.get("API_KEY", "dev-key"))
    a = p.parse_args()

    desc = (DATA / "vacancy_koz_ai_fullstack.txt").read_text(encoding="utf-8")
    v = call(f"{a.api}/api/vacancies", a.key, json.dumps({"title": "Fullstack AI Engineer", "company": "KOZ AI", "description": desc}).encode(), "application/json")
    print(f"Вакансия #{v['id']}: {len(v['requirements'])} требований")

    boundary = uuid.uuid4().hex
    parts = b""
    for f in sorted((DATA / "resumes").glob("*.txt")):
        parts += (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{f.name}"\r\nContent-Type: text/plain\r\n\r\n').encode() + f.read_bytes() + b"\r\n"
    parts += f"--{boundary}--\r\n".encode()
    q = f"?provider={a.provider}" if a.provider else ""
    cands = call(f"{a.api}/api/vacancies/{v['id']}/candidates{q}", a.key, parts, f"multipart/form-data; boundary={boundary}")
    print(f"Загружено резюме: {len(cands)}. Скрининг идёт в фоне — откройте http://localhost:3000")


if __name__ == "__main__":
    main()
