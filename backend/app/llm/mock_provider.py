"""Mock-провайдер: детерминированный эвристический baseline без внешних вызовов.

Нужен, чтобы проект запускался без API-ключей, работали тесты и CI, и чтобы в eval было с чем
сравнивать LLM (baseline на ключевых словах vs модель)."""

import json
import re
from typing import Any

from app.knowledge import find_skills, normalize, skill_positions
from app.llm.base import ChatTurn, LLMProvider, T, ToolCall, ToolSpec, Usage
from app.schemas import Requirement, RequirementList, RequirementMatch, ScreeningResult

MUST_HEADINGS = ("что мы ожидаем", "требования", "мы ожидаем", "необходимо", "обязательно")
NICE_HEADINGS = ("будет преимуществом", "плюсом", "преимуществом", "желательно", "nice to have")
VERDICT_RU = {"strong": "пригласить", "maybe": "рассмотреть", "reject": "отказ"}
SKIP_HEADINGS = ("чем предстоит", "мы предлагаем", "условия", "обязанности", "о компании", "задачи")


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


def extract_requirements(description: str) -> list[Requirement]:
    reqs: list[Requirement] = []
    lines = [raw.strip().lstrip("-•*·").strip() for raw in description.splitlines()]

    def is_heading(line: str) -> bool:
        low = normalize(line)
        return line.endswith(":") or (len(line) < 40 and any(h in low for h in MUST_HEADINGS + NICE_HEADINGS + SKIP_HEADINGS))

    has_headings = any(is_heading(x) for x in lines if x)
    mode: str | None = None
    saw_heading = False
    for line in lines:
        if not line:
            continue
        low = normalize(line)
        if has_headings and not saw_heading and not is_heading(line):
            continue  # вводный текст о компании до первого заголовка
        if is_heading(line):
            saw_heading = True
            if any(h in low for h in NICE_HEADINGS):
                mode = "nice"
            elif any(h in low for h in MUST_HEADINGS):
                mode = "must"
            else:
                mode = None
            continue
        if mode is None and saw_heading:
            continue
        if len(line) < 15:
            continue
        skills = sorted(find_skills(line))
        reqs.append(Requirement(id=f"r{len(reqs) + 1}", text=line, kind=mode or "must", category=skills[0] if skills else "soft"))
    return reqs


def _snippet(text: str, pos: int, width: int = 90) -> str:
    start = max(0, text.rfind("\n", 0, pos) + 1)
    end = text.find("\n", pos)
    end = len(text) if end < 0 else end
    line = text[start:end].strip()
    return line if len(line) <= width * 2 else line[: width * 2] + "…"


def heuristic_screen(requirements: list[dict], resume: str) -> ScreeningResult:
    resume_skills = find_skills(resume)
    matches: list[RequirementMatch] = []
    for r in requirements:
        need = find_skills(r["text"]) - {"b2b", "production"} if len(find_skills(r["text"])) > 2 else find_skills(r["text"])
        if not need:
            matches.append(RequirementMatch(requirement_id=r["id"], status="partial", comment="Soft skill — проверить на интервью"))
            continue
        found = sorted(need & resume_skills)
        ratio = len(found) / len(need)
        status = "met" if ratio >= 0.5 else "partial" if found else "missing"
        evidence = ""
        if found:
            pos = skill_positions(resume, found[0])
            evidence = _snippet(resume, pos[0]) if pos else ""
        comment = f"Найдено: {', '.join(found)}" if found else f"Нет упоминаний: {', '.join(sorted(need))}"
        matches.append(RequirementMatch(requirement_id=r["id"], status=status, evidence=evidence, comment=comment))

    years = None
    m = re.search(r"(\d+(?:[.,]\d)?)\+?\s*(?:год|лет|years)", normalize(resume))
    if m:
        years = float(m.group(1).replace(",", "."))
    seniority = "unknown" if years is None else "junior" if years < 2 else "middle" if years < 5 else "senior"

    by_id = {r["id"]: r for r in requirements}
    missing_must = [by_id[x.requirement_id]["text"] for x in matches if x.status == "missing" and by_id[x.requirement_id]["kind"] == "must"]
    met = [by_id[x.requirement_id]["text"] for x in matches if x.status == "met"]
    questions = [f"Был ли у вас опыт: «{t[:80]}»? Приведите пример." for t in missing_must[:3]]
    questions += [f"Расскажите о проекте, где вы применяли: «{t[:80]}». Какая была ваша роль?" for t in met[:2]]
    return ScreeningResult(
        candidate_name="",
        seniority=seniority,
        years_of_experience=years,
        matches=matches,
        strengths=[f"Опыт: {s}" for s in sorted(resume_skills)[:8]],
        risks=[f"Не подтверждено: {t[:90]}" for t in missing_must[:5]],
        interview_questions=questions,
        summary=f"Эвристическая оценка по ключевым словам. Совпало навыков: {len(resume_skills)}.",
    )


class MockProvider(LLMProvider):
    name = "mock"

    def structured(self, system: str, user: str, schema: type[T], task: str = "", payload: Any = None) -> tuple[T, Usage]:
        if task == "extract_requirements":
            result: Any = RequirementList(requirements=extract_requirements(payload))
        elif task == "screen":
            result = heuristic_screen(payload["requirements"], payload["resume"])
        else:
            raise ValueError(f"Mock не умеет задачу {task}")
        usage = Usage(self.name, self.model, _tokens(system + user), _tokens(result.model_dump_json()), 1)
        return result, usage  # type: ignore[return-value]

    def chat(self, system: str, messages: list[dict], tools: list[ToolSpec]) -> ChatTurn:
        last_user = next(m["content"] for m in reversed(messages) if m["role"] == "user")
        tool_results = []
        for m in reversed(messages):
            if m["role"] == "user":
                break
            if m["role"] == "tool":
                tool_results.append(m)
        usage = Usage(self.name, self.model, _tokens(system + json.dumps([str(m) for m in messages])), 50, 1)
        if tool_results:
            return ChatTurn(self._answer(tool_results[::-1]), [], usage)
        return ChatTurn("", [self._route(last_user)], usage)

    @staticmethod
    def _route(text: str) -> ToolCall:
        low = normalize(text)
        ids = [int(x) for x in re.findall(r"(?<![\w])#?(\d+)(?![\w])", text)]  # «Битрикс24», «1С» — не id
        if any(w in low for w in ("crm", "битрикс", "bitrix", "1с", "1c", "экспорт", "выгруз")) and ids:
            system = "1c" if ("1с" in low or "1c" in low) else "bitrix24"
            return ToolCall("call_1", "export_candidate", {"candidate_id": ids[0], "system": system})
        if "сравн" in low and len(ids) >= 2:
            return ToolCall("call_1", "compare_candidates", {"candidate_ids": ids[:4]})
        if any(w in low for w in ("топ", "лучш", "рейтинг", "ранж", "кого пригласить", "шорт")):
            return ToolCall("call_1", "rank_candidates", {"limit": ids[0] if ids and ids[0] <= 20 else 5})
        if ids and any(w in low for w in ("кандидат", "резюме", "подробн", "#")):
            return ToolCall("call_1", "get_candidate", {"candidate_id": ids[0]})
        return ToolCall("call_1", "search_candidates", {"query": text, "limit": 5})

    @staticmethod
    def _answer(results: list[dict]) -> str:
        parts = []
        for r in results:
            data = json.loads(r["content"])
            if isinstance(data, dict) and data.get("error"):
                parts.append(f"Ошибка: {data['error']}")
            elif r["name"] in ("rank_candidates", "search_candidates", "compare_candidates"):
                rows = data if isinstance(data, list) else data.get("items", [])
                if not rows:
                    parts.append("Ничего не нашёл.")
                for i, c in enumerate(rows, 1):
                    score = f"{c['score']:.0f}/100" if c.get("score") is not None else "—"
                    extra = f" — {c['snippet']}" if c.get("snippet") else ""
                    verdict = VERDICT_RU.get(c.get("verdict") or "", "нет оценки")
                    parts.append(f"{i}. #{c['id']} {c.get('name') or c.get('filename')}: {score}, {verdict}{extra}")
            elif r["name"] == "get_candidate":
                s = data.get("screening") or {}
                parts.append(
                    f"#{data['id']} {data.get('name')}: {data.get('score')} баллов, {VERDICT_RU.get(data.get('verdict') or '', 'нет оценки')}.\n"
                    f"Сильные стороны: {'; '.join(s.get('strengths', [])[:4])}\nРиски: {'; '.join(s.get('risks', [])[:3]) or 'нет'}"
                )
            else:
                parts.append(json.dumps(data, ensure_ascii=False))
        return "\n".join(parts)
