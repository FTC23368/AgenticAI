"""Claude planner + plan refiner."""
from ..config import settings
from ..schemas import DatasetProfile, Plan, PlanCritique
from .client import claude_json

PLAN_SCHEMA = """{
  "question": "string — restated user question",
  "assumptions": ["string"],
  "steps": [
    {
      "id": 1,
      "skill": "data-profiling | data-cleaning | exploratory-analysis | statistical-testing | time-series | ml-modeling | sql-analysis | visualization | insight-narration | data-quality",
      "intent": "one-line goal",
      "inputs": {"df_id": "string", "...": "..."},
      "expected_output": "what success looks like (chart, finding, model, table)"
    }
  ],
  "risks": ["string — what could go wrong"]
}"""

PLANNER_SYSTEM = """You are the Planner for a data-analysis agent. Given a user's question and a dataset profile, design a numbered, minimal plan of analysis steps. Each step names exactly one Skill and the inputs needed.

Principles:
- Profile first, model last. Always begin with a data-profiling and data-quality pass.
- Pick the smallest set of steps that conclusively answers the question.
- Every claim in the final report must come from a step in the plan — if you cannot trace a desired insight back to a step, add the step.
- Visualization is not optional: pair every analytical finding with a chart of the right type.
- Surface real risks (small sample, missing data, confounders) in the `risks` field; do not invent risks.
"""

REFINER_SYSTEM = """You are the same Planner, now refining the plan after a peer review.

Apply EVERY suggested change unless it conflicts with the data profile or the user's question. If you reject a suggestion, justify it briefly in `assumptions`. Renumber steps so they are sequential. Keep the plan minimal."""


def call_planner(question: str, profile: DatasetProfile, tracer) -> Plan:
    user = f"USER QUESTION:\n{question}\n\nDATASET PROFILE:\n{profile.model_dump_json(indent=2)}"
    raw = claude_json(
        model=settings.MODEL_PLANNER,
        system=PLANNER_SYSTEM,
        user=user,
        schema_hint=PLAN_SCHEMA,
        tracer=tracer,
    )
    return Plan.model_validate(raw)


def call_plan_refiner(plan: Plan, critique: PlanCritique, profile: DatasetProfile, tracer) -> Plan:
    user = (
        f"ORIGINAL PLAN:\n{plan.model_dump_json(indent=2)}\n\n"
        f"PEER CRITIQUE:\n{critique.model_dump_json(indent=2)}\n\n"
        f"DATASET PROFILE (for reference):\n{profile.model_dump_json(indent=2)}"
    )
    raw = claude_json(
        model=settings.MODEL_PLANNER,
        system=REFINER_SYSTEM,
        user=user,
        schema_hint=PLAN_SCHEMA,
        tracer=tracer,
    )
    return Plan.model_validate(raw)
