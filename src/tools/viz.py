"""Charting tools — each returns a chart_id and saves a PNG to runs/<run_id>/charts/."""
import base64
import uuid
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from ..schemas import ChartRef
from .registry import tool

sns.set_theme(style="whitegrid", palette="deep", font="DejaVu Sans")


def _save(state, fig, chart_type: str, caption: str) -> dict:
    chart_id = f"chart_{uuid.uuid4().hex[:8]}"
    path = state.charts_dir / f"{chart_id}.png"
    fig.savefig(path, dpi=110, bbox_inches="tight")
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    ref = ChartRef(chart_id=chart_id, type=chart_type, caption=caption, png_path=str(path))
    state.charts[chart_id] = ref
    return {"chart_id": chart_id, "type": chart_type, "caption": caption, "mime": "image/png", "base64": b64}


@tool(
    name="plot_bar",
    description="Bar chart of categorical x vs numeric y. Use when comparing discrete categories.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "x": {"type": "string"},
            "y": {"type": "string"},
            "title": {"type": "string", "default": ""},
        },
        "required": ["df_id", "x", "y"],
    },
    skill="visualization",
)
def t_bar(state, df_id: str, x: str, y: str, title: str = ""):
    df = state.get_df(df_id)
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=df, x=x, y=y, ax=ax, errorbar=None)
    ax.set_title(title or f"{y} by {x}")
    plt.xticks(rotation=30, ha="right")
    return _save(state, fig, "bar", title or f"Bar chart of {y} by {x}")


@tool(
    name="plot_line",
    description="Line chart for time series or ordered numeric x vs y.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "x": {"type": "string"},
            "y": {"type": "string"},
            "title": {"type": "string", "default": ""},
        },
        "required": ["df_id", "x", "y"],
    },
    skill="visualization",
)
def t_line(state, df_id: str, x: str, y: str, title: str = ""):
    df = state.get_df(df_id).sort_values(x)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sns.lineplot(data=df, x=x, y=y, ax=ax, marker="o")
    ax.set_title(title or f"{y} over {x}")
    plt.xticks(rotation=30, ha="right")
    return _save(state, fig, "line", title or f"Line chart of {y} over {x}")


@tool(
    name="plot_pie",
    description="Pie chart of a categorical column's value counts. Best with ≤7 categories.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "col": {"type": "string"},
            "title": {"type": "string", "default": ""},
        },
        "required": ["df_id", "col"],
    },
    skill="visualization",
)
def t_pie(state, df_id: str, col: str, title: str = ""):
    counts = state.get_df(df_id)[col].value_counts().head(7)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(counts.values, labels=counts.index.astype(str), autopct="%1.1f%%", startangle=90)
    ax.set_title(title or f"Share of {col}")
    return _save(state, fig, "pie", title or f"Share of {col}")


@tool(
    name="plot_scatter",
    description="Scatter plot of x vs y, optionally colored by a hue column. For correlations.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "x": {"type": "string"},
            "y": {"type": "string"},
            "hue": {"type": ["string", "null"]},
            "title": {"type": "string", "default": ""},
        },
        "required": ["df_id", "x", "y"],
    },
    skill="visualization",
)
def t_scatter(state, df_id: str, x: str, y: str, hue: str | None = None, title: str = ""):
    df = state.get_df(df_id)
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.scatterplot(data=df, x=x, y=y, hue=hue, ax=ax, alpha=0.7)
    ax.set_title(title or f"{y} vs {x}")
    return _save(state, fig, "scatter", title or f"{y} vs {x}")


@tool(
    name="plot_box",
    description="Box plot of numeric y across categories of x. Shows distribution per group.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "x": {"type": "string"},
            "y": {"type": "string"},
            "title": {"type": "string", "default": ""},
        },
        "required": ["df_id", "x", "y"],
    },
    skill="visualization",
)
def t_box(state, df_id: str, x: str, y: str, title: str = ""):
    df = state.get_df(df_id)
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=df, x=x, y=y, ax=ax)
    ax.set_title(title or f"Distribution of {y} by {x}")
    plt.xticks(rotation=30, ha="right")
    return _save(state, fig, "box", title or f"Distribution of {y} by {x}")


@tool(
    name="plot_histogram",
    description="Histogram of a numeric column.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "col": {"type": "string"},
            "bins": {"type": "integer", "default": 30},
            "title": {"type": "string", "default": ""},
        },
        "required": ["df_id", "col"],
    },
    skill="visualization",
)
def t_hist(state, df_id: str, col: str, bins: int = 30, title: str = ""):
    df = state.get_df(df_id)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.histplot(df[col].dropna(), bins=bins, kde=True, ax=ax)
    ax.set_title(title or f"Distribution of {col}")
    return _save(state, fig, "histogram", title or f"Distribution of {col}")


@tool(
    name="plot_heatmap",
    description="Correlation heatmap across numeric columns.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "cols": {"type": "array", "items": {"type": "string"}},
            "title": {"type": "string", "default": ""},
        },
        "required": ["df_id"],
    },
    skill="visualization",
)
def t_heatmap(state, df_id: str, cols: list[str] | None = None, title: str = ""):
    df = state.get_df(df_id)
    if cols:
        df = df[cols]
    df = df.select_dtypes(include="number")
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(df.corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title(title or "Correlation matrix")
    return _save(state, fig, "heatmap", title or "Correlation matrix")
