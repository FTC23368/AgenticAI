# sql-analysis

**When to use**: Aggregations or joins are easier to express in SQL than in pandas, or the user phrased their question SQL-style.

**Tools**: `run_duckdb_sql`. Each registered dataframe is queryable as a table named by its df_id (e.g. `SELECT region, SUM(amount) FROM csv_0 GROUP BY region`).

**Heuristics**:
- Quote column names with spaces or capitals: `SELECT "Order Date" FROM csv_0`.
- Always inspect the schema first via `describe_dataframe` so column names are correct.
- Cap result rows in the query (`LIMIT 1000`) when exploring; use the returned `df_id` for follow-on plotting.
