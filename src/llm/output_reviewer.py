"""GPT output reviewer — critiques the draft deliverable."""
from ..config import settings
from ..schemas import DatasetProfile, Deliverable, OutputCritique, Plan
from .client import gpt_json

OUTPUT_CRITIQUE_SCHEMA = """{
  "issues": [
    {
      "severity": "blocker | major | minor",
      "target": "finding | chart | narration",
      "target_id": "finding id or chart id, or null for narration",
      "problem": "string",
      "fix": "concrete corrective action",
      "needs_tool_call": false
    }
  ],
  "overall_quality": "unacceptable | needs_work | ship_it",
  "approve_as_is": false
}"""

OUTPUT_REVIEWER_SYSTEM = """You review a draft data-analysis deliverable (findings + charts + narration) before it goes to the user. You see the original question, the dataset profile, the refined plan, and the draft.

Check for:
1. **Grounding**: every claim in the narration must be traceable to a Finding's evidence. Flag unsupported claims as `blocker`.
2. **Chart-type correctness**: pie chart with >7 slices? Time-series shown as bar? Flag as `major` and suggest the right chart.
3. **Caveat sufficiency**: small samples, high null rates, weak model fit, confounders — all must be surfaced. Flag missing caveats as `major`.
4. **Plan coverage**: does the deliverable answer the user's question, or does it sidestep it? Flag as `blocker` if so.
5. **Narration quality**: vague language, hedging, missing numbers — flag as `minor`.

If a fix requires more analysis (e.g. "you need to test for seasonality"), set `needs_tool_call: true`.

Set `approve_as_is: true` only when there are zero blockers AND zero majors."""


def call_output_reviewer(
    question: str,
    plan: Plan,
    profile: DatasetProfile,
    deliverable: Deliverable,
    tracer,
) -> OutputCritique:
    user = (
        f"USER QUESTION:\n{question}\n\n"
        f"DATASET PROFILE:\n{profile.model_dump_json(indent=2)}\n\n"
        f"REFINED PLAN:\n{plan.model_dump_json(indent=2)}\n\n"
        f"DRAFT DELIVERABLE:\n{deliverable.model_dump_json(indent=2)}"
    )
    raw = gpt_json(
        model=settings.MODEL_OUTPUT_REVIEWER,
        system=OUTPUT_REVIEWER_SYSTEM,
        user=user,
        schema_hint=OUTPUT_CRITIQUE_SCHEMA,
        tracer=tracer,
        max_tokens=2048,
    )
    return OutputCritique.model_validate(raw)
