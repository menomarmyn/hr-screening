"""Проверяем адаптеры провайдеров без сети: подменяем SDK-клиент и смотрим формат запросов/ответов."""

import json
from types import SimpleNamespace as NS

from app.llm import ToolCall, ToolSpec
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.openai_provider import OpenAICompatibleProvider
from app.schemas import RequirementList

TOOLS = [ToolSpec("rank_candidates", "rank", {"type": "object", "properties": {"limit": {"type": "integer"}}})]


def test_anthropic_structured_and_tools():
    p = AnthropicProvider("claude-haiku-5-5", "test")
    calls = []

    def create(**kw):
        calls.append(kw)
        if kw.get("tool_choice"):
            block = NS(type="tool_use", id="t0", name="submit", input={"requirements": [{"id": "r1", "text": "Python", "kind": "must"}]})
        else:
            block = NS(type="tool_use", id="t1", name="rank_candidates", input={"limit": 3})
        return NS(content=[block], usage=NS(input_tokens=1000, output_tokens=100))

    p.client = NS(messages=NS(create=create))
    res, usage = p.structured("sys", "text", RequirementList)
    assert res.requirements[0].text == "Python"
    assert calls[0]["tool_choice"] == {"type": "tool", "name": "submit"}
    assert usage.cost_usd > 0

    history = [
        {"role": "user", "content": "топ"},
        {"role": "assistant", "content": "", "tool_calls": [ToolCall("t1", "rank_candidates", {"limit": 3})]},
        {"role": "tool", "tool_call_id": "t1", "name": "rank_candidates", "content": "[]"},
    ]
    turn = p.chat("sys", history, TOOLS)
    assert turn.tool_calls[0].name == "rank_candidates"
    sent = calls[1]["messages"]
    assert sent[1]["content"][0]["type"] == "tool_use"
    assert sent[2]["content"][0] == {"type": "tool_result", "tool_use_id": "t1", "content": "[]"}


def test_openai_json_retry_and_tools():
    p = OpenAICompatibleProvider("openai", "gpt-4o-mini", "test")
    answers = iter(["не json", json.dumps({"requirements": [{"id": "r1", "text": "SQL"}]})])
    calls = []

    def create(**kw):
        calls.append(kw)
        if "tools" in kw:
            tc = NS(id="c1", function=NS(name="rank_candidates", arguments='{"limit": 2}'))
            msg = NS(content=None, tool_calls=[tc])
        else:
            msg = NS(content=next(answers), tool_calls=None)
        return NS(choices=[NS(message=msg)], usage=NS(prompt_tokens=10, completion_tokens=5))

    p.client = NS(chat=NS(completions=NS(create=create)))
    res, usage = p.structured("sys", "text", RequirementList)
    assert res.requirements[0].text == "SQL"
    assert len(calls) == 2 and usage.input_tokens == 20  # был повтор после невалидного JSON

    turn = p.chat("sys", [{"role": "user", "content": "топ"}], TOOLS)
    assert turn.tool_calls[0].arguments == {"limit": 2}
    assert calls[-1]["tools"][0]["function"]["name"] == "rank_candidates"
