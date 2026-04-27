"""Smoke tests for the tools layer — exercise each tool against a fixture dataset."""
from pathlib import Path

import pandas as pd
import pytest

from src.tools import TOOLS  # noqa: F401  (registers all tools)
from src.tools.ingestion import profile_dataset
from src.tools.registry import call_tool
from src.tools.state import SessionState


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))
    # Re-import config so it picks up the new RUNS_DIR
    from importlib import reload
    from src import config as cfg
    reload(cfg)
    s = SessionState.new(run_id="test")
    df = pd.DataFrame({
        "region": ["NA", "EU", "NA", "APAC", "EU", "NA"] * 50,
        "month": pd.date_range("2024-01-01", periods=300, freq="D"),
        "sales": [100 + i * 0.5 for i in range(300)],
        "units": [1, 2, 3, 4, 5, 6] * 50,
    })
    s.dataframes["fix_0"] = df
    return s


def test_describe_dataframe(state):
    out = call_tool("describe_dataframe", {"df_id": "fix_0"}, state)
    assert out["shape"] == [300, 4]
    assert "region" in out["dtypes"]


def test_profile_column_numeric(state):
    out = call_tool("profile_column", {"df_id": "fix_0", "col": "sales"}, state)
    assert "stats" in out and out["stats"]["min"] == 100.0


def test_value_counts(state):
    out = call_tool("value_counts", {"df_id": "fix_0", "col": "region", "n": 5}, state)
    assert out["NA"] == 150


def test_filter_rows(state):
    out = call_tool("filter_rows", {"df_id": "fix_0", "expr": "sales > 200"}, state)
    assert out["rows"] < 300 and out["rows"] > 0


def test_group_aggregate(state):
    out = call_tool(
        "group_aggregate",
        {"df_id": "fix_0", "by": ["region"], "agg": {"sales": "sum", "units": "mean"}},
        state,
    )
    assert "df_id" in out and len(out["head"]) == 3


def test_correlation(state):
    out = call_tool("compute_correlation", {"df_id": "fix_0"}, state)
    assert "sales" in out and "units" in out["sales"]


def test_outliers_iqr(state):
    out = call_tool("detect_outliers", {"df_id": "fix_0", "col": "sales", "method": "iqr"}, state)
    assert "n_outliers" in out


def test_stat_test_anova(state):
    out = call_tool(
        "run_statistical_test",
        {"df_id": "fix_0", "test": "anova", "args": {"col": "sales", "group": "region"}},
        state,
    )
    assert "p_value" in out


def test_run_duckdb_sql(state):
    out = call_tool(
        "run_duckdb_sql",
        {"sql": "SELECT region, SUM(sales) AS total FROM fix_0 GROUP BY region ORDER BY total DESC"},
        state,
    )
    assert out["shape"][0] == 3


def test_run_python(state):
    out = call_tool(
        "run_python",
        {"code": "result_df = dfs['fix_0'].groupby('region').size().reset_index(name='n')\nprint(result_df)"},
        state,
    )
    assert "df_id" in out and "stdout" in out


@pytest.mark.parametrize("tool_name,args", [
    ("plot_bar", {"df_id": "fix_0", "x": "region", "y": "sales"}),
    ("plot_line", {"df_id": "fix_0", "x": "month", "y": "sales"}),
    ("plot_pie", {"df_id": "fix_0", "col": "region"}),
    ("plot_scatter", {"df_id": "fix_0", "x": "units", "y": "sales"}),
    ("plot_box", {"df_id": "fix_0", "x": "region", "y": "sales"}),
    ("plot_histogram", {"df_id": "fix_0", "col": "sales"}),
    ("plot_heatmap", {"df_id": "fix_0"}),
])
def test_charts(state, tool_name, args):
    out = call_tool(tool_name, args, state)
    assert out["chart_id"].startswith("chart_")
    assert out["mime"] == "image/png"
    assert len(out["base64"]) > 100
    assert Path(state.charts[out["chart_id"]].png_path).exists()


def test_log_finding(state):
    state.charts["c1"] = type("Stub", (), {"chart_id": "c1"})()
    out = call_tool(
        "log_finding",
        {
            "claim": "NA region leads sales",
            "evidence": ["fix_0 totals show NA = 150 rows"],
            "confidence": "high",
            "caveats": [],
            "chart_ids": [],
        },
        state,
    )
    assert out["finding_id"].startswith("f_")
    fid = out["finding_id"]
    assert state.findings[fid].claim == "NA region leads sales"


def test_profile_dataset(state):
    p = profile_dataset(state, "fix_0")
    assert p.rows == 300 and p.cols == 4
    assert any(c["name"] == "region" for c in p.columns)


def test_tool_registry_has_all_charts():
    from src.tools.registry import TOOLS
    expected = {"plot_bar", "plot_line", "plot_pie", "plot_scatter", "plot_box", "plot_histogram", "plot_heatmap"}
    assert expected.issubset(set(TOOLS.keys()))
