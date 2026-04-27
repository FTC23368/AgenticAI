import pandas as pd

from .registry import tool


@tool(
    name="filter_rows",
    description="Filter rows of a dataframe using a pandas query expression. Returns a new df_id.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "expr": {"type": "string", "description": "pandas .query() expression, e.g. 'amount > 100 and region == \"NA\"'"},
        },
        "required": ["df_id", "expr"],
    },
)
def t_filter(state, df_id: str, expr: str):
    df = state.get_df(df_id).query(expr)
    new_id = state.register_df(df, hint="filt")
    return {"df_id": new_id, "rows": len(df)}


@tool(
    name="select_columns",
    description="Keep only the specified columns. Returns a new df_id.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "cols": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["df_id", "cols"],
    },
)
def t_select(state, df_id: str, cols: list[str]):
    df = state.get_df(df_id)[cols]
    new_id = state.register_df(df, hint="sel")
    return {"df_id": new_id, "shape": list(df.shape)}


@tool(
    name="group_aggregate",
    description="Group by columns and aggregate. agg is a dict like {'sales':'sum','units':'mean'}.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "by": {"type": "array", "items": {"type": "string"}},
            "agg": {"type": "object"},
        },
        "required": ["df_id", "by", "agg"],
    },
)
def t_group(state, df_id: str, by: list[str], agg: dict):
    df = state.get_df(df_id).groupby(by, dropna=False).agg(agg).reset_index()
    new_id = state.register_df(df, hint="grp")
    return {
        "df_id": new_id,
        "shape": list(df.shape),
        "head": df.head(10).fillna("").astype(str).to_dict("records"),
    }


@tool(
    name="join_dataframes",
    description="Join two dataframes. how is one of inner/left/right/outer.",
    input_schema={
        "type": "object",
        "properties": {
            "left": {"type": "string"},
            "right": {"type": "string"},
            "on": {"type": "array", "items": {"type": "string"}},
            "how": {"type": "string", "default": "inner"},
        },
        "required": ["left", "right", "on"],
    },
)
def t_join(state, left: str, right: str, on: list[str], how: str = "inner"):
    df = state.get_df(left).merge(state.get_df(right), on=on, how=how)
    new_id = state.register_df(df, hint="join")
    return {"df_id": new_id, "shape": list(df.shape)}


@tool(
    name="add_column",
    description="Add a new column computed from a pandas eval expression.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "name": {"type": "string"},
            "expr": {"type": "string"},
        },
        "required": ["df_id", "name", "expr"],
    },
)
def t_add_col(state, df_id: str, name: str, expr: str):
    df = state.get_df(df_id).copy()
    df[name] = df.eval(expr)
    new_id = state.register_df(df, hint="aug")
    return {"df_id": new_id, "columns": list(df.columns)}


@tool(
    name="pivot",
    description="Pivot a long dataframe to wide.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "index": {"type": ["string", "array"]},
            "columns": {"type": "string"},
            "values": {"type": "string"},
        },
        "required": ["df_id", "index", "columns", "values"],
    },
)
def t_pivot(state, df_id: str, index, columns: str, values: str):
    df = state.get_df(df_id).pivot_table(index=index, columns=columns, values=values).reset_index()
    new_id = state.register_df(df, hint="piv")
    return {"df_id": new_id, "shape": list(df.shape)}
