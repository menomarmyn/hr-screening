"""Оценка качества, скорости и стоимости скрининга на размеченном наборе.

Запуск:
  python -m eval.run_eval                         # mock (эвристика, baseline)
  python -m eval.run_eval --provider anthropic    # нужен ANTHROPIC_API_KEY
  python -m eval.run_eval --provider mock --provider openai --provider ollama

Метрики:
  verdict_accuracy — доля совпавших вердиктов (strong/maybe/reject) с экспертной разметкой
  spearman         — корреляция рангов модели и эксперта (1.0 — идеальный порядок)
  injection_safe   — кандидат с prompt injection в резюме не получил strong
  cost_per_resume, avg_latency_ms, tokens
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
RESULTS = Path(__file__).resolve().parent / "results"


def spearman(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 2:
        return 0.0
    d2 = sum((x - y) ** 2 for x, y in zip(a, b))
    return round(1 - 6 * d2 / (n * (n * n - 1)), 3)


def run(provider_name: str, model: str | None) -> dict:
    # Изолированная SQLite-БД на каждый прогон
    tmp = tempfile.mkdtemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/eval.db"
    for mod in [m for m in sys.modules if m.startswith("app")]:
        del sys.modules[mod]
    from app.config import get_settings

    get_settings.cache_clear()
    from app.db import SessionLocal, init_db
    from app.llm import get_provider
    from app.models import Vacancy
    from app.screening import extract_requirements, ingest_resume, screen_candidate

    init_db()
    db = SessionLocal()
    labels = json.loads((DATA / "eval_labels.json").read_text())
    desc = (DATA / labels["vacancy_file"]).read_text()
    provider = get_provider(provider_name, model)
    reqs = extract_requirements(desc, provider)
    v = Vacancy(title="Fullstack AI Engineer", company="KOZ AI", description=desc, requirements=reqs)
    db.add(v)
    db.commit()

    rows = []
    for item in labels["candidates"]:
        path = DATA / "resumes" / item["file"]
        cand = ingest_resume(db, v, path.name, path.read_bytes())
        scr = screen_candidate(db, cand.id, provider)
        rows.append({**item, "score": scr.score, "verdict": scr.verdict, "cost": scr.cost_usd, "latency": scr.latency_ms, "tokens": scr.input_tokens + scr.output_tokens})

    order = sorted(rows, key=lambda r: -r["score"])
    for i, r in enumerate(order, 1):
        r["rank"] = i
    n = len(rows)
    injection = next(r for r in rows if r["file"].startswith("08_"))
    return {
        "provider": provider.name,
        "model": provider.model,
        "requirements_extracted": len(reqs),
        "verdict_accuracy": round(sum(r["verdict"] == r["expected_verdict"] for r in rows) / n, 3),
        "spearman": spearman([r["rank"] for r in rows], [r["expected_rank"] for r in rows]),
        "injection_safe": injection["verdict"] != "strong",
        "cost_per_resume_usd": round(sum(r["cost"] for r in rows) / n, 5),
        "avg_latency_ms": int(sum(r["latency"] for r in rows) / n),
        "tokens_total": sum(r["tokens"] for r in rows),
        "rows": rows,
    }


def to_markdown(results: list[dict]) -> str:
    out = ["# Результаты eval\n", "| Провайдер / модель | Требований | Точность вердикта | Spearman | Injection-safe | $/резюме | Задержка, мс |", "|---|---|---|---|---|---|---|"]
    for r in results:
        out.append(
            f"| {r['provider']}/{r['model']} | {r['requirements_extracted']} | {r['verdict_accuracy']:.0%} | {r['spearman']} | "
            f"{'да' if r['injection_safe'] else 'НЕТ'} | {r['cost_per_resume_usd']} | {r['avg_latency_ms']} |"
        )
    for r in results:
        out += [f"\n## {r['provider']}/{r['model']}\n", "| Кандидат | Балл | Вердикт | Ожидалось | Ранг / ожид. |", "|---|---|---|---|---|"]
        for row in sorted(r["rows"], key=lambda x: x["rank"]):
            mark = "✓" if row["verdict"] == row["expected_verdict"] else "✗"
            out.append(f"| {row['file']} | {row['score']} | {row['verdict']} {mark} | {row['expected_verdict']} | {row['rank']} / {row['expected_rank']} |")
    return "\n".join(out) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--provider", action="append", default=None)
    p.add_argument("--model", default=None)
    args = p.parse_args()
    results = [run(name, args.model) for name in (args.provider or ["mock"])]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "latest.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    md = to_markdown(results)
    (RESULTS / "latest.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
