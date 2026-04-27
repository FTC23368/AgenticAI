# exploratory-analysis

**When to use**: To find the structure of relationships in the data — group differences, correlations, segment behavior — before committing to a model or test.

**Tools**: `group_aggregate`, `pivot`, `compute_correlation`, `value_counts`, `plot_bar`, `plot_box`, `plot_heatmap`, `run_duckdb_sql`.

**Heuristics**:
- For a "what drives X" question, start with grouped means/medians of X across the strongest categorical and numeric covariates.
- Always inspect distributions (`plot_box` or `plot_histogram`) before reporting means — a single outlier can mislead.
- Heatmap correlations only over numeric columns; never silently drop non-numerics without saying so.
- Log findings as you go with `log_finding` so the narrator has structured material to work from.
