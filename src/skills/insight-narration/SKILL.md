# insight-narration

**When to use**: After analysis is complete and findings are logged. Translates numeric results into plain English the user can act on.

**Tools**: `log_finding`, `list_artifacts` (no plotting tools — only describe what already exists).

**Style**:
- Lead with the answer to the user's exact question.
- Use specific numbers, not vague language ("revenue fell 12% in Q3", not "revenue declined notably").
- Quote evidence: cite the chart_id or finding_id that supports each claim.
- Surface caveats explicitly — sample size, confounders, missing data — even when the headline is strong.
- One short paragraph per finding. No bullet-point soup; readable prose.

**Forbidden**:
- Speculating about causes the data does not show.
- Restating what the chart already shows ("the chart shows X"); say what it means instead.
- Hedging every sentence ("might possibly suggest"). State the finding, then qualify with one explicit caveat.
