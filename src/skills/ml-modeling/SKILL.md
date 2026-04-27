# ml-modeling

**When to use**: The user wants to know what predicts an outcome, or the relative importance of multiple drivers.

**Tools**: `fit_regression`, `fit_classifier`, `feature_importance` (returned by the fit tools).

**Heuristics**:
- Use `random_forest` by default — it handles non-linearity and gives feature importances out of the box.
- Use `linear` / `logistic` only when the user explicitly wants interpretable coefficients.
- Always report the held-out metric (R² for regression, accuracy for classification) and the top 5 features by importance.
- Report a caveat when the model is weak (R² < 0.3 or accuracy near baseline) — do NOT narrate feature importances from a model that does not fit.
