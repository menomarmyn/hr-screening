"""OpenAI и все OpenAI-совместимые API: Google Gemini (endpoint /v1beta/openai), Ollama, vLLM."""

import json
from typing import Any

from app.llm.base import ChatTurn, LLMError, LLMProvider, T, ToolCall, ToolSpec, Usage, parse_json_model

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _sampling(model: str) -> dict:
    """Reasoning-модели OpenAI (gpt-5*, o-серия) не принимают temperature — передаём только остальным."""
    return {} if model.startswith(("gpt-5", "o1", "o3", "o4")) else {"temperature": 0}


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, name: str, model: str, api_key: str, base_url: str | None = None):
        super().__init__(model)
        from openai import OpenAI

        self.name = name
        self.client = OpenAI(api_key=api_key, base_url=base_url, max_retries=3, timeout=120)

    def structured(self, system: str, user: str, schema: type[T], task: str = "", payload: Any = None) -> tuple[T, Usage]:
        schema_txt = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        sys = f"{system}\n\nОтвечай ТОЛЬКО валидным JSON по этой JSON Schema:\n{schema_txt}"
        messages = [{"role": "system", "content": sys}, {"role": "user", "content": user}]
        total = Usage(self.name, self.model)
        # JSON mode + валидация pydantic + один повтор с текстом ошибки (локальные модели иногда ошибаются)
        for attempt in range(2):
            t0 = self._timer()
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages, response_format={"type": "json_object"}, **_sampling(self.model)
            )
            u = resp.usage
            total.add(Usage(self.name, self.model, u.prompt_tokens if u else 0, u.completion_tokens if u else 0, self._ms(t0)))
            raw = resp.choices[0].message.content or ""
            try:
                return parse_json_model(raw, schema), total
            except LLMError as e:
                if attempt == 1:
                    raise
                messages += [{"role": "assistant", "content": raw}, {"role": "user", "content": f"Исправь ответ: {e}"}]
        raise LLMError("unreachable")

    def _convert(self, system: str, messages: list[dict]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            if m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
            elif m["role"] == "assistant" and m.get("tool_calls"):
                out.append(
                    {
                        "role": "assistant",
                        "content": m.get("content") or None,
                        "tool_calls": [
                            {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)}}
                            for tc in m["tool_calls"]
                        ],
                    }
                )
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def chat(self, system: str, messages: list[dict], tools: list[ToolSpec]) -> ChatTurn:
        t0 = self._timer()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=self._convert(system, messages),
            tools=[{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}} for t in tools],
            **_sampling(self.model),
        )
        u = resp.usage
        usage = Usage(self.name, self.model, u.prompt_tokens if u else 0, u.completion_tokens if u else 0, self._ms(t0))
        msg = resp.choices[0].message
        calls = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(tc.id, tc.function.name, args))
        return ChatTurn(msg.content or "", calls, usage)
