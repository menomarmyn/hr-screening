import json
import time
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# Цена за 1M токенов (input, output) в USD. Ориентировочные значения — сверяйте с прайсом
# провайдера и переопределяйте при необходимости. Локальные модели считаем бесплатными.
PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (1.0, 5.0),
    "claude-sonnet-5-5": (3.0, 15.0),
    "claude-opus-5-5": (5.0, 25.0),
    "gpt-5-mini": (0.25, 2.0),
    "gpt-5-nano": (0.05, 0.4),
    "gpt-4o-mini": (0.15, 0.6),
    "gpt-4o": (2.5, 10.0),
    "gemini-2.5-flash": (0.3, 2.5),
}


@dataclass
class Usage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0

    @property
    def cost_usd(self) -> float:
        pin, pout = PRICES.get(self.model, (0.0, 0.0))
        return round((self.input_tokens * pin + self.output_tokens * pout) / 1_000_000, 6)

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.latency_ms += other.latency_ms

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
        }


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON Schema


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatTurn:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage | None = None


class LLMError(RuntimeError):
    pass


class LLMProvider:
    """Единый интерфейс поверх разных LLM.

    Сообщения в нейтральном формате:
      {"role": "user"|"assistant", "content": str, "tool_calls": [ToolCall...]}
      {"role": "tool", "tool_call_id": str, "name": str, "content": str}
    """

    name = "base"

    def __init__(self, model: str):
        self.model = model

    # --- structured output ---
    def structured(self, system: str, user: str, schema: type[T], task: str = "", payload: Any = None) -> tuple[T, Usage]:
        raise NotImplementedError

    # --- function calling ---
    def chat(self, system: str, messages: list[dict], tools: list[ToolSpec]) -> ChatTurn:
        raise NotImplementedError

    # helpers
    def _timer(self) -> float:
        return time.perf_counter()

    def _ms(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)


def parse_json_model(raw: str, schema: type[T]) -> T:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") :]
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < 0:
        raise LLMError("Модель вернула не JSON")
    try:
        return schema.model_validate(json.loads(raw[start : end + 1]))
    except (json.JSONDecodeError, ValidationError) as e:
        raise LLMError(f"Ответ не прошёл валидацию схемы: {e}") from e
