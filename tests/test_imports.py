"""Sanity: every module imports without API keys present."""


def test_imports():
    import src.app  # noqa: F401
    import src.orchestrator  # noqa: F401
    import src.schemas  # noqa: F401
    from src.tools import TOOLS  # noqa: F401
    assert "load_csv" in TOOLS
    assert "log_finding" in TOOLS
    assert "plot_bar" in TOOLS


def test_schemas_round_trip():
    from src.schemas import Plan, PlanStep, Finding, Deliverable, ChartRef, OutputCritique, OutputIssue
    p = Plan(question="q", steps=[PlanStep(id=1, skill="exploratory-analysis", intent="x", expected_output="y")])
    assert Plan.model_validate_json(p.model_dump_json()).question == "q"
    f = Finding(id="f_1", claim="c", evidence=["e"], confidence="high")
    d = Deliverable(findings=[f], charts=[ChartRef(chart_id="c1", type="bar", caption="cap", png_path="/tmp/x.png")], narration="n")
    assert Deliverable.model_validate_json(d.model_dump_json()).narration == "n"
    crit = OutputCritique(issues=[OutputIssue(severity="major", target="finding", problem="p", fix="f")])
    assert OutputCritique.model_validate_json(crit.model_dump_json()).issues[0].severity == "major"
