"""MCP-сервер: те же инструменты, что у встроенного агента, доступны любому MCP-клиенту
(Claude Desktop, Claude Code, Cursor). Запуск: python -m app.mcp_server

Пример конфигурации для Claude Desktop (claude_desktop_config.json):
{
  "mcpServers": {
    "hr-screener": {
      "command": "python", "args": ["-m", "app.mcp_server"],
      "cwd": "/path/to/backend",
      "env": {"DATABASE_URL": "postgresql+psycopg://hr:hr@localhost:5432/hr"}
    }
  }
}
"""

import json

try:  # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP

from app import tools
from app.db import SessionLocal, init_db
from app.models import Vacancy

mcp = FastMCP("hr-screener")


def _run(fn, *args, **kwargs) -> str:
    db = SessionLocal()
    try:
        return json.dumps(fn(db, *args, **kwargs), ensure_ascii=False, default=str)
    except Exception as e:  # noqa: BLE001
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


@mcp.tool()
def list_vacancies() -> str:
    """Список вакансий с id."""
    db = SessionLocal()
    try:
        return json.dumps([{"id": v.id, "title": v.title, "company": v.company} for v in db.query(Vacancy)], ensure_ascii=False)
    finally:
        db.close()


@mcp.tool()
def vacancy_requirements(vacancy_id: int) -> str:
    """Требования вакансии."""
    return _run(tools.vacancy_requirements, vacancy_id)


@mcp.tool()
def rank_candidates(vacancy_id: int, limit: int = 5, verdict: str | None = None) -> str:
    """Рейтинг кандидатов вакансии по баллу AI-скрининга. verdict: strong|maybe|reject."""
    return _run(tools.rank_candidates, vacancy_id, limit=limit, verdict=verdict)


@mcp.tool()
def search_candidates(vacancy_id: int, query: str, limit: int = 5) -> str:
    """Семантический поиск по резюме кандидатов вакансии."""
    return _run(tools.search_candidates, vacancy_id, query=query, limit=limit)


@mcp.tool()
def get_candidate(vacancy_id: int, candidate_id: int) -> str:
    """Результат скрининга кандидата: оценка по требованиям, риски, вопросы для интервью."""
    return _run(tools.get_candidate, vacancy_id, candidate_id=candidate_id)


@mcp.tool()
def compare_candidates(vacancy_id: int, candidate_ids: list[int]) -> str:
    """Сравнение кандидатов по матрице требований."""
    return _run(tools.compare_candidates, vacancy_id, candidate_ids=candidate_ids)


@mcp.tool()
def export_candidate(vacancy_id: int, candidate_id: int, system: str = "bitrix24") -> str:
    """Выгрузить кандидата в Битрикс24 или 1С (system: bitrix24|1c)."""
    return _run(tools.export_candidate, vacancy_id, candidate_id=candidate_id, system=system)


if __name__ == "__main__":
    init_db()
    mcp.run()
