"""Claude narrator — turns findings into plain-English. Two modes: draft (one-shot) and final (streamed)."""
from __future__ import annotations
from typing import AsyncIterator

from ..config import settings
from ..schemas import Deliverable
from .client import anthropic_client, claude_stream

NARRATOR_SYSTEM = """You are the Narrator for a data-analysis agent. You receive a structured set of Findings and ChartRefs, and you write a clear, plain-English explanation that answers the user's question.

Style:
- Lead with the headline answer in one sentence.
- Then 2–5 short paragraphs, each anchored on a single finding.
- Refer to charts by their caption ("the bar chart of sales by region shows…"), never by chart_id.
- State concrete numbers, not vague language.
- Surface the caveats from the findings honestly.
- Do not invent data. If the findings are thin, say so.
- No bullet-point soup. Readable prose.
- Markdown allowed — bold for the headline answer, no headings."""


def call_narrator_draft(question: str, deliverable: Deliverable, tracer) -> str:
    user = (
        f"USER QUESTION:\n{question}\n\n"
        f"DELIVERABLE (structured findings + charts):\n{deliverable.model_dump_json(indent=2)}"
    )
    resp = anthropic_client().messages.create(
        model=settings.MODEL_NARRATOR,
        max_tokens=2048,
        temperature=0.3,
        system=NARRATOR_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    tracer.add_tokens(resp.usage.input_tokens, resp.usage.output_tokens)
    tracer.log("llm.narrator_draft", in_t=resp.usage.input_tokens, out_t=resp.usage.output_tokens)
    return text


def stream_final(question: str, deliverable: Deliverable, tracer):
    """Generator yielding text tokens of the final narration."""
    user = (
        f"USER QUESTION:\n{question}\n\n"
        f"DELIVERABLE (structured findings + charts):\n{deliverable.model_dump_json(indent=2)}"
    )
    yield from claude_stream(
        model=settings.MODEL_NARRATOR,
        system=NARRATOR_SYSTEM,
        user=user,
        tracer=tracer,
        max_tokens=2048,
    )
