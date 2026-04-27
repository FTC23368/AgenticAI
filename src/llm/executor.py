"""Claude executor — runs the refined plan via tool use, accumulating findings & charts."""
from __future__ import annotations
import asyncio
import json

from ..config import settings
from ..schemas import Plan
from ..tools import tool_specs
from ..tools.registry import call_tool

EXECUTOR_SYSTEM = """You are the Executor for a data-analysis agent. You have been given:
1. The user's question.
2. A refined, peer-reviewed plan.
3. A dataset already loaded (df_id provided).
4. A toolbox covering profiling, cleaning, EDA, stats, time-series, ML, SQL, and visualization.

Run through the plan step by step. For each step:
- Call the tools for that step.
- Inspect results before moving on — do NOT call the next step's tools blindly.
- After producing a substantive result (group comparison, test, model fit, chart), call `log_finding` with the claim, evidence (tool result values or chart_ids), confidence, and any caveats.
- Pair every finding with at least one chart from `plot_*`.

Be efficient. Skip steps if their precondition has already been satisfied. Stop when the plan is complete."""


async def run_executor(state, plan: Plan, question: str, df_id: str) -> None:
    """Drive the Claude tool-use loop until stop_reason == 'end_turn' or step cap hit."""
    from .client import claude_tools

    tools = tool_specs()
    user = (
        f"USER QUESTION:\n{question}\n\n"
        f"REFINED PLAN:\n{plan.model_dump_json(indent=2)}\n\n"
        f"PRIMARY DATAFRAME df_id: {df_id}\n"
    )
    messages: list[dict] = [{"role": "user", "content": user}]

    for step in range(settings.MAX_EXECUTOR_STEPS):
        resp = claude_tools(
            model=settings.MODEL_EXECUTOR,
            system=EXECUTOR_SYSTEM,
            messages=messages,
            tools=tools,
            tracer=state.tracer,
            max_tokens=4096,
        )
        # Append assistant turn verbatim so tool_use ids line up
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            break

        tool_results = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            name = block.name
            args = block.input or {}
            state.tracer.log("tool.call", name=name, args=args)
            try:
                # call_tool is sync — run in executor to keep loop responsive
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: call_tool(name, args, state)
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str)[:8000],
                })
                state.tracer.log("tool.ok", name=name)

                # Stream chart and finding events to the user as they happen
                if isinstance(result, dict) and result.get("chart_id"):
                    cid = result["chart_id"]
                    payload = {
                        "chart_id": cid,
                        "type": result.get("type"),
                        "caption": result.get("caption"),
                        "mime": result.get("mime"),
                        "base64": result.get("base64"),
                    }
                    await state.emit("chart_draft", payload)
                if isinstance(result, dict) and result.get("finding_id"):
                    f = state.findings[result["finding_id"]]
                    await state.emit("finding_draft", f.model_dump())
            except Exception as e:
                state.tracer.log("tool.error", name=name, error=str(e))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"error": str(e)}),
                    "is_error": True,
                })

        messages.append({"role": "user", "content": tool_results})
