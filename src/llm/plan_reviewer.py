"""GPT plan reviewer — critiques the Claude-drafted plan."""
from ..config import settings
from ..schemas import DatasetProfile, Plan, PlanCritique
from .client import gpt_json

CRITIQUE_SCHEMA = """{
  "issues": ["string — concrete problems with the plan"],
  "suggested_changes": ["string — specific actionable edits, e.g. 'Add a step to test for seasonality before forecasting'"],
  "approve_as_is": true
}"""

REVIEWER_SYSTEM = """You are an independent reviewer of an analysis plan drafted by another model. You see the same dataset profile and user question. Your job is to find real issues — gaps, wrong methods, missing checks, confounders, missing visualizations, unstated assumptions — not to nitpick style.

Score the plan strictly:
- If the plan would mislead the user, set approve_as_is=false and list blockers.
- If the plan is structurally sound, return approve_as_is=true with at most minor suggestions.

Be specific. "Add error bars" is good. "Improve rigor" is not.
"""


def call_plan_reviewer(plan: Plan, profile: DatasetProfile, tracer) -> PlanCritique:
    user = (
        f"PLAN UNDER REVIEW:\n{plan.model_dump_json(indent=2)}\n\n"
        f"DATASET PROFILE:\n{profile.model_dump_json(indent=2)}"
    )
    raw = gpt_json(
        model=settings.MODEL_PLAN_REVIEWER,
        system=REVIEWER_SYSTEM,
        user=user,
        schema_hint=CRITIQUE_SCHEMA,
        tracer=tracer,
    )
    return PlanCritique.model_validate(raw)
