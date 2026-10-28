from typing import Any

from app.llm.base import ChatTurn, LLMProvider, T, ToolCall, ToolSpec, Usage


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str, api_key: str):
        super().__init__(model)
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key, max_retries=3, timeout=60)

    def structured(self, system: str, user: str, schema: type[T], task: str = "", payload: Any = None) -> tuple[T, Usage]:
        # Structured output через принудительный вызов инструмента: модель обязана вернуть JSON по схеме
        tool = {"name": "submit", "description": "Верни результат строго по схеме", "input_schema": schema.model_json_schema()}
        t0 = self._timer()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit"},
        )
        usage = Usage(self.name, self.model, resp.usage.input_tokens, resp.usage.output_tokens, self._ms(t0))
        block = next(b for b in resp.content if b.type == "tool_use")
        return schema.model_validate(block.input), usage

    def _convert(self, messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
            elif m["role"] == "assistant" and m.get("tool_calls"):
                content: list[dict] = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                content += [{"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments} for tc in m["tool_calls"]]
                out.append({"role": "assistant", "content": content})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def chat(self, system: str, messages: list[dict], tools: list[ToolSpec]) -> ChatTurn:
        t0 = self._timer()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=self._convert(messages),
            tools=[{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools],
        )
        usage = Usage(self.name, self.model, resp.usage.input_tokens, resp.usage.output_tokens, self._ms(t0))
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        return ChatTurn(text, calls, usage)


