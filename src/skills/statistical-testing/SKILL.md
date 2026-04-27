# statistical-testing

**When to use**: When the user's question implies a comparison ("is A different from B?", "did X change?", "are these related?") and a numeric answer with a confidence claim is required.

**Tools**: `run_statistical_test` (ttest_ind, ttest_1samp, chisquare, anova, mannwhitneyu, pearsonr).

**Picking the right test**:
- Two independent groups, numeric outcome → `ttest_ind` (or `mannwhitneyu` if non-normal).
- ≥3 groups, numeric outcome → `anova`.
- Two categorical variables → `chisquare`.
- Two numeric variables, linear relationship → `pearsonr`.
- One sample vs a known mean → `ttest_1samp`.

**Reporting**: state the test name, the p-value, the effect direction in plain English, and a caveat about assumptions (normality, independence). Do not claim "significant" without an alpha threshold (default 0.05).
