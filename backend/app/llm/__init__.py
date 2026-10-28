from app.config import Settings, get_settings
from app.llm.base import ChatTurn, LLMError, LLMProvider, ToolCall, ToolSpec, Usage

DEFAULT_MODELS = {
    "mock": "heuristic-v1",
    "anthropic": "claude-haiku-5-5",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "ollama": "qwen2.5:7b",
}


def get_provider(name: str | None = None, model: str | None = None, settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    name = (name or s.llm_provider).lower()
    model = model or (s.llm_model if name == s.llm_provider else "") or DEFAULT_MODELS.get(name, "")

    if name == "mock":
        from app.llm.mock_provider import MockProvider

        return MockProvider(model)
    if name == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        if not s.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY не задан")
        return AnthropicProvider(model, s.anthropic_api_key)

    from app.llm.openai_provider import GEMINI_BASE_URL, OpenAICompatibleProvider

    if name == "openai":
        if not s.openai_api_key:
            raise LLMError("OPENAI_API_KEY не задан")
        return OpenAICompatibleProvider("openai", model, s.openai_api_key)
    if name == "gemini":
        if not s.google_api_key:
            raise LLMError("GOOGLE_API_KEY не задан")
        return OpenAICompatibleProvider("gemini", model, s.google_api_key, GEMINI_BASE_URL)
    if name == "ollama":
        return OpenAICompatibleProvider("ollama", model, "ollama", s.ollama_base_url)
    raise LLMError(f"Неизвестный провайдер: {name}")


__all__ = ["ChatTurn", "LLMError", "LLMProvider", "ToolCall", "ToolSpec", "Usage", "get_provider", "DEFAULT_MODELS"]
