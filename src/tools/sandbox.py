"""Code execution tools — DuckDB SQL on registered dataframes, restricted Python eval."""
import io
import textwrap
import traceback
from contextlib import redirect_stdout

import duckdb
import pandas as pd

from .registry import tool


@tool(
    name="run_duckdb_sql",
    description=(
        "Run a DuckDB SQL query. Each registered dataframe is available as a table named by its df_id "
        "(e.g. SELECT * FROM csv_0). Returns up to 100 rows of the result and a new df_id holding the full result."
    ),
    input_schema={
        "type": "object",
        "properties": {"sql": {"type": "string"}},
        "required": ["sql"],
    },
    skill="sql-analysis",
)
def t_duckdb(state, sql: str):
    con = duckdb.connect()
    for df_id, df in state.dataframes.items():
        con.register(df_id, df)
    try:
        result = con.execute(sql).df()
    except Exception as e:
        return {"error": str(e)}
    new_id = state.register_df(result, hint="sql")
    return {
        "df_id": new_id,
        "shape": list(result.shape),
        "head": result.head(20).fillna("").astype(str).to_dict("records"),
    }


@tool(
    name="run_python",
    description=(
        "Execute a short Python snippet for analysis. Available names: pd (pandas), np (numpy), "
        "and a dict `dfs` mapping df_id → DataFrame. Print results — only stdout is returned. "
        "To create a new dataframe accessible later, set a variable named `result_df` and the tool will register it."
    ),
    input_schema={
        "type": "object",
        "properties": {"code": {"type": "string"}},
        "required": ["code"],
    },
)
def t_run_python(state, code: str):
    import numpy as np  # local import to keep registry fast
    g = {"pd": pd, "np": np, "dfs": state.dataframes, "__builtins__": __builtins__}
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            exec(textwrap.dedent(code), g)
    except Exception:
        return {"error": traceback.format_exc(limit=3), "stdout": buf.getvalue()}
    out = {"stdout": buf.getvalue()[:4000]}
    if "result_df" in g and isinstance(g["result_df"], pd.DataFrame):
        out["df_id"] = state.register_df(g["result_df"], hint="py")
    return out
