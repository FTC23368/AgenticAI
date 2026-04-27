# data-cleaning

**When to use**: After profiling reveals nulls, duplicates, type mismatches, or outliers that would distort downstream analysis.

**Tools**: `filter_rows`, `select_columns`, `add_column`, `run_python` (for `dropna`, `fillna`, `astype`, dedup).

**Heuristics**:
- Drop a column only if null rate > 60% AND the column is unlikely to be the target.
- Impute with median for numeric, mode for categorical when nulls < 30%.
- Convert obvious date strings to datetime via `run_python` before time-series steps.
- Always create a new df via the tool's returned df_id; never overwrite the original.

**Output**: a cleaned df_id documented in a `log_finding` describing what was changed and why.
