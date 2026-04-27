import pandas as pd

from .registry import tool


@tool(
    name="describe_dataframe",
    description="Schema, shape, dtypes, head, and per-column null counts for a dataframe.",
    input_schema={
        "type": "object",
        "properties": {"df_id": {"type": "string"}},
        "required": ["df_id"],
    },
)
def t_describe(state, df_id: str):
    df = state.get_df(df_id)
    return {
        "shape": list(df.shape),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "nulls": {c: int(df[c].isna().sum()) for c in df.columns},
        "head": df.head(5).fillna("").astype(str).to_dict("records"),
    }


@tool(
    name="profile_column",
    description="Distribution stats, unique count, top values, and null rate for a single column.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "col": {"type": "string"},
        },
        "required": ["df_id", "col"],
    },
)
def t_profile_column(state, df_id: str, col: str):
    s = state.get_df(df_id)[col]
    out = {
        "dtype": str(s.dtype),
        "null_pct": round(float(s.isna().mean()) * 100, 2),
        "unique": int(s.nunique(dropna=True)),
    }
    if pd.api.types.is_numeric_dtype(s):
        d = s.describe()
        out["stats"] = {k: float(d[k]) for k in ["mean", "std", "min", "25%", "50%", "75%", "max"]}
    else:
        out["top_values"] = s.value_counts(dropna=True).head(10).to_dict()
    return out


@tool(
    name="value_counts",
    description="Top-N value counts for a column.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "col": {"type": "string"},
            "n": {"type": "integer", "default": 20},
        },
        "required": ["df_id", "col"],
    },
)
def t_value_counts(state, df_id: str, col: str, n: int = 20):
    return state.get_df(df_id)[col].value_counts(dropna=True).head(n).to_dict()


@tool(
    name="sample_rows",
    description="Random sample of rows from a dataframe.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "n": {"type": "integer", "default": 10},
            "seed": {"type": "integer", "default": 42},
        },
        "required": ["df_id"],
    },
)
def t_sample(state, df_id: str, n: int = 10, seed: int = 42):
    df = state.get_df(df_id)
    return df.sample(n=min(n, len(df)), random_state=seed).fillna("").astype(str).to_dict("records")
