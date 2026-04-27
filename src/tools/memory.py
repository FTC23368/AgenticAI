import uuid

from ..schemas import Finding
from .registry import tool


@tool(
    name="save_artifact",
    description="Save an arbitrary JSON-serializable value under a name for later retrieval in this run.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}, "value": {}},
        "required": ["name", "value"],
    },
)
def t_save_artifact(state, name: str, value):
    state.artifacts[name] = value
    return {"saved": name}


@tool(
    name="load_artifact",
    description="Load a previously saved artifact by name.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
)
def t_load_artifact(state, name: str):
    if name not in state.artifacts:
        return {"error": f"no such artifact: {name}"}
    return {"value": state.artifacts[name]}


@tool(
    name="log_finding",
    description=(
        "Record a finding with claim, supporting evidence, confidence, optional caveats, and chart_ids. "
        "Findings drive the final narration — make claims specific and grounded in data you have already computed."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "claim": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "caveats": {"type": "array", "items": {"type": "string"}},
            "chart_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["claim", "evidence", "confidence"],
    },
    skill="insight-narration",
)
def t_log_finding(
    state,
    claim: str,
    evidence: list[str],
    confidence: str,
    caveats: list[str] | None = None,
    chart_ids: list[str] | None = None,
):
    fid = f"f_{uuid.uuid4().hex[:6]}"
    f = Finding(
        id=fid,
        claim=claim,
        evidence=evidence,
        confidence=confidence,  # type: ignore
        caveats=caveats or [],
        chart_ids=chart_ids or [],
    )
    state.findings[fid] = f
    return {"finding_id": fid}


@tool(
    name="list_artifacts",
    description="List all artifacts, dataframes, charts, and findings registered in this run.",
    input_schema={"type": "object", "properties": {}},
)
def t_list(state):
    return {
        "dataframes": {k: list(v.shape) for k, v in state.dataframes.items()},
        "charts": [{"id": c.chart_id, "type": c.type} for c in state.charts.values()],
        "findings": [{"id": f.id, "claim": f.claim} for f in state.findings.values()],
        "artifacts": list(state.artifacts.keys()),
        "models": list(state.models.keys()),
    }
