"""Словарь навыков: синонимы технологий. Используется для нормализации текста, эвристического
baseline-скрининга (mock-провайдер) и аналитики по навыкам."""

import re

SKILLS: dict[str, list[str]] = {
    "python": ["python", "питон"],
    "typescript": ["typescript", "ts"],
    "javascript": ["javascript", "js", "node.js", "nodejs"],
    "react": ["react", "next.js", "nextjs"],
    "fastapi": ["fastapi", "fast api"],
    "django/flask": ["django", "flask"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "sql": ["sql"],
    "redis": ["redis"],
    "rest api": ["rest", "rest api", "api"],
    "git": ["git", "github", "gitlab"],
    "docker": ["docker", "контейнер"],
    "docker compose": ["docker compose", "docker-compose"],
    "linux": ["linux", "ubuntu", "debian"],
    "llm": ["llm", "openai", "anthropic", "claude", "gpt", "gemini", "языков", "chatgpt"],
    "rag": ["rag", "retrieval"],
    "embeddings": ["embedding", "embeddings", "эмбеддинг", "векторн"],
    "ai agents": ["агент", "agent", "agents", "function calling", "tool calling", "tool use"],
    "multi-agent": ["многоагент", "multi-agent", "multiagent", "crewai", "autogen"],
    "langchain": ["langchain"],
    "langgraph": ["langgraph"],
    "llamaindex": ["llamaindex", "llama-index", "llama index"],
    "mcp": ["mcp", "model context protocol"],
    "vector db": ["pgvector", "qdrant", "chroma", "faiss", "weaviate", "pinecone", "milvus"],
    "local llm": ["ollama", "vllm", "llama.cpp", "локальн", "self-hosted", "qwen", "mistral", "llama 3"],
    "celery": ["celery", "rq", "dramatiq"],
    "clickhouse": ["clickhouse"],
    "etl": ["etl", "elt", "airflow", "dbt"],
    "ci/cd": ["ci/cd", "github actions", "gitlab ci", "jenkins", "ci"],
    "1c": ["1с", "1c", "1с:"],
    "erp/crm": ["erp", "crm", "bitrix", "битрикс", "amocrm", "sap", "salesforce"],
    "bi": ["bi", "power bi", "superset", "metabase", "tableau", "дашборд", "аналитическ"],
    "security": ["безопасност", "security", "owasp", "jwt", "oauth", "rbac"],
    "b2b": ["b2b", "корпоративн", "заказчик", "клиент"],
    "production": ["production", "прод", "продакшн", "внедрен", "запуск", "deployment"],
    "ai dev tools": ["cursor", "copilot", "claude code", "codeium", "windsurf", "ai-инструмент"],
    "testing": ["pytest", "тест", "jest", "unit", "vitest"],
}

# Слова, которые слишком часто дают ложные совпадения при поиске подстрокой
_SHORT = {"ts", "js", "ci", "bi", "api", "rq", "sql", "git", "rag", "mcp", "llm", "gpt", "erp", "crm", "etl", "elt", "1c", "1с"}


def normalize(text: str) -> str:
    return text.lower().replace("ё", "е")


def _has(text: str, term: str) -> bool:
    if term in _SHORT or len(term) <= 3:
        return re.search(rf"(?<![a-zа-я0-9]){re.escape(term)}(?![a-zа-я0-9])", text) is not None
    return term in text


def find_skills(text: str) -> set[str]:
    t = normalize(text)
    return {skill for skill, terms in SKILLS.items() if any(_has(t, term) for term in terms)}


def skill_positions(text: str, skill: str) -> list[int]:
    t = normalize(text)
    pos = []
    for term in SKILLS[skill]:
        if term in _SHORT or len(term) <= 3:
            pos += [m.start() for m in re.finditer(rf"(?<![a-zа-я0-9]){re.escape(term)}(?![a-zа-я0-9])", t)]
        else:
            start = t.find(term)
            if start >= 0:
                pos.append(start)
    return sorted(pos)
