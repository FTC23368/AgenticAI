# time-series

**When to use**: Data has a date/time column and the question asks about trend, seasonality, change over time, or forecasting.

**Tools**: `time_series_decompose`, `plot_line`, `group_aggregate` (for weekly/monthly rollups), `run_python` (for resampling and rolling windows).

**Workflow**:
1. Coerce the date column to datetime via `run_python` if not already.
2. Sort and resample to a regular frequency (D, W, M) before plotting.
3. Use `plot_line` for the headline series.
4. Call `time_series_decompose` to separate trend, seasonality, and residual.
5. Report the trend direction with magnitude (e.g. "+18% from Jan to Sep") and call out seasonal cycles.

**Caveats to surface**: short series (<2 full periods), missing dates, mixed time zones.
