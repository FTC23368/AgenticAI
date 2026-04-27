from typing import Literal, Optional
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    id: int
    skill: str
    intent: str
    inputs: dict = Field(default_factory=dict)
    expected_output: str


class Plan(BaseModel):
    question: str
    assumptions: list[str] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class PlanCritique(BaseModel):
    issues: list[str] = Field(default_factory=list)
    suggested_changes: list[str] = Field(default_factory=list)
    approve_as_is: bool = False


class ChartRef(BaseModel):
    chart_id: str
    type: Literal["bar", "line", "pie", "scatter", "box", "histogram", "heatmap"]
    caption: str
    png_path: str


class Finding(BaseModel):
    id: str
    claim: str
    evidence: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    caveats: list[str] = Field(default_factory=list)
    chart_ids: list[str] = Field(default_factory=list)


class Deliverable(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    charts: list[ChartRef] = Field(default_factory=list)
    narration: str = ""


class OutputIssue(BaseModel):
    severity: Literal["blocker", "major", "minor"]
    target: Literal["finding", "chart", "narration"]
    target_id: Optional[str] = None
    problem: str
    fix: str
    needs_tool_call: bool = False


class OutputCritique(BaseModel):
    issues: list[OutputIssue] = Field(default_factory=list)
    overall_quality: Literal["unacceptable", "needs_work", "ship_it"] = "needs_work"
    approve_as_is: bool = False


class DatasetProfile(BaseModel):
    file_name: str
    rows: int
    cols: int
    columns: list[dict]
    head: list[dict]
