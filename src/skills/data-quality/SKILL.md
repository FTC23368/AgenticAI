# data-quality

**When to use**: Before trusting any finding, sanity-check the data for issues that would invalidate it — outliers, missing data, schema oddities, duplicate rows.

**Tools**: `detect_outliers`, `describe_dataframe`, `value_counts`, `run_python` (for `df.duplicated()`).

**Checklist**:
1. Per-column null rate (already in profile) — flag any column >30%.
2. Outliers via IQR for each numeric column relevant to the question.
3. Duplicate rows count.
4. Inconsistent categorical values (e.g. "USA" vs "U.S." vs "us") — surface via `value_counts`.

Log each material issue as a `log_finding` with confidence "low" if it could change conclusions, so the narrator can fold caveats into the final report.
