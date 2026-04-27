# visualization

**When to use**: Every finding worth narrating deserves a chart. Pick the chart type based on what is being shown, not what is most convenient.

**Tools**: `plot_bar`, `plot_line`, `plot_pie`, `plot_scatter`, `plot_box`, `plot_histogram`, `plot_heatmap`.

**Chart-picking rules**:
- **Time on x-axis** → `plot_line`.
- **Comparing a numeric across discrete categories** → `plot_bar` (≤20 categories) or `plot_box` (when distribution matters).
- **Two numerics' relationship** → `plot_scatter`.
- **Single numeric distribution** → `plot_histogram`.
- **Share / composition** → `plot_pie` ONLY when ≤7 categories AND parts sum to a meaningful whole. Otherwise prefer `plot_bar`.
- **Correlation matrix** → `plot_heatmap`.

Always pass an explicit `title`. Always attach the returned `chart_id` to the supporting `log_finding` call.
