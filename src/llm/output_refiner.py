"""Claude output refiner — applies the GPT critique to the deliverable.

May issue follow-up tool calls when the critique flags `needs_tool_call=true` (missing evidence).
"""
from __future__ import annotations
import asyncio
import json

from ..config import settings
from ..schemas import Deliverable, Finding, OutputCritique, ChartRef
from ..tools import tool_specs
from ..tools.registry import call_tool
from .client import anthropic_client

REFINER_SYSTEM = """You are the Output Refiner. You receive a draft deliverable (findings + charts + narration) and a peer critique. Your job is to produce an improved deliverable.

Apply every blocker and major issue. For each:
- If `target=finding`: rewrite the claim, add caveats, drop unsupported parts.
- If `target=chart` and the type is wrong: call the correct `plot_*` tool to regenerate, then update the supporting Finding's chart_ids.
- If `target=narration`: rewrite the relevant paragraph(s).
- If `needs_tool_call=true`: call the appropriate analysis tool to gather the missing evidence, then update the affected Finding.

When done, output a single JSON Deliverable (no prose). Schema:
{
  "findings": [{"id":"...", "claim":"...", "evidence":[...], "confidence":"low|medium|high", "caveats":[...], "chart_ids":[...]}],
  "charts":   [{"chart_id":"...", "type":"bar|line|pie|scatter|box|histogram|heatmap", "caption":"...", "png_path":"..."}],
  "narration": "string — rewritten plain-English explanation"
}"""


async def call_output_refiner(
    deliverable: Deliverable,
    critique: OutputCritique,
    state,
) -> Deliverable:
    tools = tool_specs()
    user = (
        f"DRAFT DELIVERABLE:\n{deliverable.model_dump_json(indent=2)}\n\n"
        f"CRITIQUE:\n{critique.model_dump_json(indent=2)}\n\n"
        f"AVAILABLE DATAFRAMES: {list(state.dataframes.keys())}\n"
        f"EXISTING CHARTS: {[c.chart_id for c in state.charts.values()]}\n"
        f"EXISTING FINDINGS: {[f.id for f in state.findings.values()]}\n"
    )
    messages: list[dict] = [{"role": "user", "content": user}]

    for _ in range(8):  # bounded refiner loop
        resp = anthropic_client().messages.create(
            model=settings.MODEL_OUTPUT_REFINER,
            max_tokens=4096,
            temperature=0,
            system=REFINER_SYSTEM,
            tools=tools,
            messages=messages,
        )
        state.tracer.add_tokens(resp.usage.input_tokens, resp.usage.output_tokens)
        state.tracer.log("llm.output_refiner", in_t=resp.usage.input_tokens, out_t=resp.usage.output_tokens, stop=resp.stop_reason)
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
            return _parse_deliverable(text, deliverable, state)

        tool_results = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: call_tool(block.name, block.input or {}, state)
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str)[:8000],
                })
            except Exception as e:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"error": str(e)}),
                    "is_error": True,
                })
        messages.append({"role": "user", "content": tool_results})

    # Hit loop cap — return draft as fallback
    return deliverable


def _parse_deliverable(text: str, draft: Deliverable, state) -> Deliverable:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    try:
        raw = json.loads(text)
    except Exception:
        # Fallback: keep draft, replace narration with whatever the model produced
        return Deliverable(findings=draft.findings, charts=draft.charts, narration=text or draft.narration)

    findings = [Finding.model_validate(f) for f in raw.get("findings", [])]
    charts_raw = raw.get("charts", [])
    charts: list[ChartRef] = []
    for c in charts_raw:
        if c.get("chart_id") in state.charts:
            charts.append(state.charts[c["chart_id"]])
        else:
            try:
                charts.append(ChartRef.model_validate(c))
            except Exception:
                continue
    return Deliverable(findings=findings, charts=charts, narration=raw.get("narration", draft.narration))
