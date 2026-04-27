"""End-to-end run: profile → plan loop → execute → output loop → stream final."""
from __future__ import annotations
import asyncio

from .config import settings
from .guardrails import GuardrailError
from .llm.executor import run_executor
from .llm.narrator import call_narrator_draft, stream_final
from .llm.output_refiner import call_output_refiner
from .llm.output_reviewer import call_output_reviewer
from .llm.plan_reviewer import call_plan_reviewer
from .llm.planner import call_plan_refiner, call_planner
from .schemas import Deliverable
from .tools.ingestion import load_uploaded, profile_dataset


async def run_analysis(state, file_name: str, question: str) -> None:
    try:
        # 1. Load + profile (deterministic, no LLM)
        df_id = load_uploaded(state, file_name, hint="csv")
        profile = profile_dataset(state, df_id)
        await state.emit("profile", profile.model_dump())

        # 2-4. PLAN (with optional reflection loop)
        plan = await asyncio.get_event_loop().run_in_executor(
            None, lambda: call_planner(question, profile, state.tracer)
        )
        await state.emit("plan_draft", plan.model_dump())

        if settings.ENABLE_PLAN_REFLECTION:
            for round_idx in range(settings.MAX_PLAN_ROUNDS):
                critique = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: call_plan_reviewer(plan, profile, state.tracer)
                )
                await state.emit("plan_critique", {**critique.model_dump(), "round": round_idx + 1})
                if critique.approve_as_is:
                    break
                plan = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: call_plan_refiner(plan, critique, profile, state.tracer)
                )
        await state.emit("plan_final", plan.model_dump())

        # 5. EXECUTE — Claude tool use produces draft charts + findings via SSE
        await run_executor(state, plan, question, df_id)

        # Assemble draft deliverable from accumulated state
        draft_narration = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: call_narrator_draft(
                question,
                Deliverable(
                    findings=list(state.findings.values()),
                    charts=list(state.charts.values()),
                    narration="",
                ),
                state.tracer,
            ),
        )
        deliverable = Deliverable(
            findings=list(state.findings.values()),
            charts=list(state.charts.values()),
            narration=draft_narration,
        )

        # 6-7. OUTPUT reflection loop (optional)
        if settings.ENABLE_OUTPUT_REFLECTION:
            for round_idx in range(settings.MAX_OUTPUT_ROUNDS):
                critique = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: call_output_reviewer(question, plan, profile, deliverable, state.tracer),
                )
                await state.emit("output_critique", {**critique.model_dump(), "round": round_idx + 1})
                if critique.approve_as_is:
                    break
                deliverable = await call_output_refiner(deliverable, critique, state)

        # Emit final charts + findings (post-refinement)
        for chart in deliverable.charts:
            ref = state.charts.get(chart.chart_id)
            if ref is None:
                continue
            import base64
            with open(ref.png_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            await state.emit("chart", {
                "chart_id": ref.chart_id,
                "type": ref.type,
                "caption": ref.caption,
                "mime": "image/png",
                "base64": b64,
            })
        for f in deliverable.findings:
            await state.emit("finding", f.model_dump())

        # 8. STREAM the final narration token-by-token
        loop = asyncio.get_event_loop()
        gen = await loop.run_in_executor(
            None, lambda: stream_final(question, deliverable, state.tracer)
        )
        # gen is a generator (sync) — drain in executor, push tokens to queue
        def _drain(q):
            for tok in gen:
                asyncio.run_coroutine_threadsafe(state.emit("token", tok), loop).result()
        await loop.run_in_executor(None, _drain, state.sse_queue)

        await state.emit("done", {
            "run_id": state.run_id,
            "tokens_in": state.tracer.tokens_in,
            "tokens_out": state.tracer.tokens_out,
            "n_findings": len(deliverable.findings),
            "n_charts": len(deliverable.charts),
        })

    except GuardrailError as e:
        await state.emit("done", {"run_id": state.run_id, "error": str(e)})
    except Exception as e:
        state.tracer.log("orchestrator.error", error=repr(e))
        await state.emit("done", {"run_id": state.run_id, "error": repr(e)})
    finally:
        await state.sse_queue.put(None)  # sentinel: end stream
