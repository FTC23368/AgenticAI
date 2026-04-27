"""Claude planner + plan refiner."""
from ..config import settings
from ..schemas import DatasetProfile, Plan, PlanCritique
from .client import claude_json

PLANNER_SYSTEM = """You are the Planner for a data-analysis agent. Given a user's question and a dataset profile, design a numbered, minimal plan of analysis steps. Each step names exactly one Skill and the inputs needed.

Available skills (use the exact names): data-profiling, data-cleaning, exploratory-analysis, statistical-testing, time-series, ml-modeling, sql-analysis, visualization, insight-narration, data-quality.

HARD CONSTRAINTS:
- **Maximum 10 steps total.** Aggregate work into broader steps rather than splitting hairs.
- Every analytical step that produces a visual MUST set its `chart` field to the planned chart's `type` and `title`. Allowed types: bar, line, pie, scatter, box, histogram, heatmap. Steps that don't produce a chart (profiling, narration) leave `chart` null.
- Pick the right chart type for the data: time-series → line; numeric across discrete categories → bar; share/composition with ≤7 categories → pie; correlation matrix → heatmap; distribution → histogram or box; two numerics' relationship → scatter.
- Do NOT pre-engineer features the data does not need; do NOT plan multi-stage statistical audits unless the question requires them.

Principles:
- Profile first, narrate last. Always begin with one data-profiling step and end with one insight-narration step.
- Pick the smallest set of steps that conclusively answers the question — usually 4-8 steps.
- Surface real risks (small sample, missing data, confounders) in the `risks` field; do not invent risks.

Submit the plan by calling the submit_plan tool."""

REFINER_SYSTEM = """You are the same Planner, now refining the plan after a peer review.

Apply EVERY suggested change unless it conflicts with the data profile or the user's question. If you reject a suggestion, justify it briefly in `assumptions`. Renumber steps so they are sequential. Keep the plan minimal.

Submit the refined plan by calling the submit_plan tool."""


def call_planner(question: str, profile: DatasetProfile, tracer) -> Plan:
    user = f"USER QUESTION:\n{question}\n\nDATASET PROFILE:\n{profile.model_dump_json(indent=2)}"
    raw = claude_json(
        model=settings.MODEL_PLANNER,
        system=PLANNER_SYSTEM,
        user=user,
        schema=Plan.model_json_schema(),
        tracer=tracer,
        tool_name="submit_plan",
        tool_description="Submit the analysis plan.",
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
        schema=Plan.model_json_schema(),
        tracer=tracer,
        tool_name="submit_plan",
        tool_description="Submit the refined analysis plan.",
    )
    return Plan.model_validate(raw)
