"""Thin wrappers over Anthropic and OpenAI SDKs with tracing + token accounting."""
from __future__ import annotations
import json
from typing import Any, Iterable

from anthropic import Anthropic
from openai import OpenAI

from ..config import settings
from ..guardrails import check_token_budget

_anthropic: Anthropic | None = None
_openai: OpenAI | None = None


def anthropic_client() -> Anthropic:
    global _anthropic
    if _anthropic is None:
        _anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic


def openai_client() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai


# ---------- Anthropic ----------

def claude_json(
    model: str,
    system: str,
    user: str,
    schema_hint: str,
    tracer,
    max_tokens: int = 4096,
) -> dict:
    """Ask Claude for a JSON object matching schema_hint. Returns parsed dict."""
    full_system = (
        system
        + "\n\nReturn ONLY a valid JSON object that conforms to this schema. No prose, no markdown fences:\n"
        + schema_hint
    )
    resp = anthropic_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        system=full_system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    tracer.add_tokens(resp.usage.input_tokens, resp.usage.output_tokens)
    tracer.log("llm.claude_json", model=model, in_t=resp.usage.input_tokens, out_t=resp.usage.output_tokens)
    check_token_budget(tracer.total_tokens)
    return _parse_json(text)


def claude_tools(
    model: str,
    system: str,
    messages: list[dict],
    tools: list[dict],
    tracer,
    max_tokens: int = 4096,
):
    """One round of Claude tool use. Returns the raw response object."""
    resp = anthropic_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        system=system,
        tools=tools,
        messages=messages,
    )
    tracer.add_tokens(resp.usage.input_tokens, resp.usage.output_tokens)
    tracer.log("llm.claude_tools", model=model, in_t=resp.usage.input_tokens, out_t=resp.usage.output_tokens, stop=resp.stop_reason)
    check_token_budget(tracer.total_tokens)
    return resp


def claude_stream(
    model: str,
    system: str,
    user: str,
    tracer,
    max_tokens: int = 2048,
) -> Iterable[str]:
    """Yield text tokens from Claude as they stream."""
    with anthropic_client().messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=0.3,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for chunk in stream.text_stream:
            yield chunk
        final = stream.get_final_message()
    tracer.add_tokens(final.usage.input_tokens, final.usage.output_tokens)
    tracer.log("llm.claude_stream", model=model, in_t=final.usage.input_tokens, out_t=final.usage.output_tokens)
    check_token_budget(tracer.total_tokens)


# ---------- OpenAI ----------

def gpt_json(
    model: str,
    system: str,
    user: str,
    schema_hint: str,
    tracer,
    max_tokens: int = 2048,
) -> dict:
    """Ask GPT for a JSON object using response_format=json_object."""
    full_system = (
        system
        + "\n\nReturn ONLY a valid JSON object that conforms to this schema:\n"
        + schema_hint
    )
    resp = openai_client().chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": full_system},
            {"role": "user", "content": user},
        ],
    )
    usage = resp.usage
    tracer.add_tokens(usage.prompt_tokens, usage.completion_tokens)
    tracer.log("llm.gpt_json", model=model, in_t=usage.prompt_tokens, out_t=usage.completion_tokens)
    check_token_budget(tracer.total_tokens)
    return _parse_json(resp.choices[0].message.content or "{}")


# ---------- helpers ----------

def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Best-effort: find first {...} block
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise
