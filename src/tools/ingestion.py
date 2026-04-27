from pathlib import Path

import pandas as pd

from ..guardrails import enforce_file_size, enforce_row_limit
from ..schemas import DatasetProfile
from .registry import tool


def _load(path: Path) -> pd.DataFrame:
    enforce_file_size(path)
    suf = path.suffix.lower()
    if suf == ".csv":
        df = pd.read_csv(path)
    elif suf in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif suf == ".json":
        df = pd.read_json(path)
    elif suf == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file type: {suf}")
    return enforce_row_limit(df)


def load_uploaded(state, file_name: str, hint: str = "df") -> str:
    """Internal helper used by the orchestrator to load the user's upload."""
    path = state.upload_dir / file_name
    df = _load(path)
    return state.register_df(df, hint=hint)


def profile_dataset(state, df_id: str) -> DatasetProfile:
    """Profile a dataframe — used deterministically before the planner runs."""
    df = state.get_df(df_id)
    cols = []
    for c in df.columns:
        s = df[c]
        cols.append({
            "name": c,
            "dtype": str(s.dtype),
            "null_pct": round(float(s.isna().mean()) * 100, 2),
            "unique": int(s.nunique(dropna=True)),
            "sample": [str(v) for v in s.dropna().head(3).tolist()],
        })
    return DatasetProfile(
        file_name=df_id,
        rows=int(len(df)),
        cols=int(len(df.columns)),
        columns=cols,
        head=df.head(5).fillna("").astype(str).to_dict("records"),
    )


@tool(
    name="load_csv",
    description="Load a CSV file from the upload directory and register it as a dataframe. Returns df_id.",
    input_schema={
        "type": "object",
        "properties": {"file_name": {"type": "string"}},
        "required": ["file_name"],
    },
    skill="data-profiling",
)
def t_load_csv(state, file_name: str):
    df = _load(state.upload_dir / file_name)
    return {"df_id": state.register_df(df, hint="csv"), "shape": list(df.shape)}


@tool(
    name="load_excel",
    description="Load an Excel sheet. Returns df_id.",
    input_schema={
        "type": "object",
        "properties": {
            "file_name": {"type": "string"},
            "sheet": {"type": ["string", "integer"], "default": 0},
        },
        "required": ["file_name"],
    },
    skill="data-profiling",
)
def t_load_excel(state, file_name: str, sheet=0):
    df = pd.read_excel(state.upload_dir / file_name, sheet_name=sheet)
    df = enforce_row_limit(df)
    return {"df_id": state.register_df(df, hint="xlsx"), "shape": list(df.shape)}


@tool(
    name="load_json",
    description="Load a JSON file as a dataframe. Returns df_id.",
    input_schema={
        "type": "object",
        "properties": {"file_name": {"type": "string"}},
        "required": ["file_name"],
    },
    skill="data-profiling",
)
def t_load_json(state, file_name: str):
    df = enforce_row_limit(pd.read_json(state.upload_dir / file_name))
    return {"df_id": state.register_df(df, hint="json"), "shape": list(df.shape)}


@tool(
    name="load_parquet",
    description="Load a Parquet file as a dataframe. Returns df_id.",
    input_schema={
        "type": "object",
        "properties": {"file_name": {"type": "string"}},
        "required": ["file_name"],
    },
    skill="data-profiling",
)
def t_load_parquet(state, file_name: str):
    df = enforce_row_limit(pd.read_parquet(state.upload_dir / file_name))
    return {"df_id": state.register_df(df, hint="parquet"), "shape": list(df.shape)}


@tool(
    name="list_uploaded_files",
    description="List files the user has uploaded for this run.",
    input_schema={"type": "object", "properties": {}},
)
def t_list_uploaded(state):
    return {"files": [p.name for p in state.upload_dir.iterdir() if p.is_file()]}
