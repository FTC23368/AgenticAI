import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from .registry import tool


@tool(
    name="compute_correlation",
    description="Pearson/spearman correlation matrix for numeric columns.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "cols": {"type": "array", "items": {"type": "string"}},
            "method": {"type": "string", "enum": ["pearson", "spearman", "kendall"], "default": "pearson"},
        },
        "required": ["df_id"],
    },
    skill="exploratory-analysis",
)
def t_corr(state, df_id: str, cols: list[str] | None = None, method: str = "pearson"):
    df = state.get_df(df_id)
    if cols:
        df = df[cols]
    df = df.select_dtypes(include="number")
    return df.corr(method=method).round(3).to_dict()


@tool(
    name="detect_outliers",
    description="Flag outliers in a numeric column. method: iqr, zscore, or isolation_forest.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "col": {"type": "string"},
            "method": {"type": "string", "enum": ["iqr", "zscore", "isolation_forest"], "default": "iqr"},
        },
        "required": ["df_id", "col"],
    },
    skill="data-quality",
)
def t_outliers(state, df_id: str, col: str, method: str = "iqr"):
    s = state.get_df(df_id)[col].dropna()
    if method == "iqr":
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        mask = (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
    elif method == "zscore":
        z = (s - s.mean()) / s.std()
        mask = z.abs() > 3
    else:
        iso = IsolationForest(random_state=42, contamination="auto").fit(s.values.reshape(-1, 1))
        mask = pd.Series(iso.predict(s.values.reshape(-1, 1)) == -1, index=s.index)
    return {
        "method": method,
        "n_outliers": int(mask.sum()),
        "n_total": int(len(s)),
        "outlier_pct": round(float(mask.mean()) * 100, 2),
    }


@tool(
    name="run_statistical_test",
    description="Run a hypothesis test. test ∈ {ttest_ind, ttest_1samp, chisquare, anova, mannwhitneyu, pearsonr}.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "test": {"type": "string"},
            "args": {"type": "object", "description": "test-specific args, e.g. {'col':'x','group':'g'} for ttest_ind"},
        },
        "required": ["df_id", "test", "args"],
    },
    skill="statistical-testing",
)
def t_stat_test(state, df_id: str, test: str, args: dict):
    df = state.get_df(df_id)
    if test == "ttest_ind":
        col, group = args["col"], args["group"]
        groups = df[group].dropna().unique()
        if len(groups) != 2:
            return {"error": f"ttest_ind needs exactly 2 groups, got {len(groups)}"}
        a = df[df[group] == groups[0]][col].dropna()
        b = df[df[group] == groups[1]][col].dropna()
        t, p = stats.ttest_ind(a, b, equal_var=False)
        return {"test": test, "groups": [str(g) for g in groups], "t": float(t), "p_value": float(p),
                "mean_a": float(a.mean()), "mean_b": float(b.mean()), "n_a": int(len(a)), "n_b": int(len(b))}
    if test == "ttest_1samp":
        t, p = stats.ttest_1samp(df[args["col"]].dropna(), args["popmean"])
        return {"test": test, "t": float(t), "p_value": float(p)}
    if test == "chisquare":
        ct = pd.crosstab(df[args["row"]], df[args["col"]])
        chi2, p, dof, _ = stats.chi2_contingency(ct)
        return {"test": test, "chi2": float(chi2), "p_value": float(p), "dof": int(dof)}
    if test == "anova":
        groups = [g[args["col"]].dropna().values for _, g in df.groupby(args["group"])]
        f, p = stats.f_oneway(*groups)
        return {"test": test, "F": float(f), "p_value": float(p)}
    if test == "mannwhitneyu":
        col, group = args["col"], args["group"]
        gs = df[group].dropna().unique()
        a = df[df[group] == gs[0]][col].dropna()
        b = df[df[group] == gs[1]][col].dropna()
        u, p = stats.mannwhitneyu(a, b)
        return {"test": test, "U": float(u), "p_value": float(p)}
    if test == "pearsonr":
        r, p = stats.pearsonr(df[args["x"]].dropna(), df[args["y"]].dropna())
        return {"test": test, "r": float(r), "p_value": float(p)}
    return {"error": f"unknown test: {test}"}


def _xy(df, target, features):
    X = df[features].select_dtypes(include="number").fillna(0)
    y = df[target]
    return X, y


@tool(
    name="fit_regression",
    description="Train a regression model and return metrics + feature importances. model ∈ {linear, random_forest}.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "target": {"type": "string"},
            "features": {"type": "array", "items": {"type": "string"}},
            "model": {"type": "string", "default": "random_forest"},
        },
        "required": ["df_id", "target", "features"],
    },
    skill="ml-modeling",
)
def t_fit_reg(state, df_id: str, target: str, features: list[str], model: str = "random_forest"):
    X, y = _xy(state.get_df(df_id).dropna(subset=[target]), target, features)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    m = LinearRegression() if model == "linear" else RandomForestRegressor(n_estimators=200, random_state=42)
    m.fit(Xtr, ytr)
    pred = m.predict(Xte)
    model_id = f"reg_{len(state.models)}"
    state.models[model_id] = (m, X.columns.tolist())
    imp = (
        dict(zip(X.columns, m.feature_importances_.tolist()))
        if hasattr(m, "feature_importances_")
        else dict(zip(X.columns, np.abs(m.coef_).tolist()))
    )
    return {
        "model_id": model_id,
        "r2": float(r2_score(yte, pred)),
        "mae": float(mean_absolute_error(yte, pred)),
        "feature_importance": imp,
    }


@tool(
    name="fit_classifier",
    description="Train a classifier and return accuracy + feature importances.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "target": {"type": "string"},
            "features": {"type": "array", "items": {"type": "string"}},
            "model": {"type": "string", "default": "random_forest"},
        },
        "required": ["df_id", "target", "features"],
    },
    skill="ml-modeling",
)
def t_fit_clf(state, df_id: str, target: str, features: list[str], model: str = "random_forest"):
    X, y = _xy(state.get_df(df_id).dropna(subset=[target]), target, features)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None)
    m = LogisticRegression(max_iter=500) if model == "logistic" else RandomForestClassifier(n_estimators=200, random_state=42)
    m.fit(Xtr, ytr)
    pred = m.predict(Xte)
    model_id = f"clf_{len(state.models)}"
    state.models[model_id] = (m, X.columns.tolist())
    imp = (
        dict(zip(X.columns, m.feature_importances_.tolist()))
        if hasattr(m, "feature_importances_")
        else dict(zip(X.columns, np.abs(m.coef_[0]).tolist()))
    )
    return {
        "model_id": model_id,
        "accuracy": float(accuracy_score(yte, pred)),
        "feature_importance": imp,
    }


@tool(
    name="time_series_decompose",
    description="Decompose a time series into trend, seasonal, and residual components. Returns summary stats.",
    input_schema={
        "type": "object",
        "properties": {
            "df_id": {"type": "string"},
            "date_col": {"type": "string"},
            "value_col": {"type": "string"},
            "period": {"type": "integer", "default": 12},
        },
        "required": ["df_id", "date_col", "value_col"],
    },
    skill="time-series",
)
def t_ts_decompose(state, df_id: str, date_col: str, value_col: str, period: int = 12):
    from statsmodels.tsa.seasonal import seasonal_decompose
    df = state.get_df(df_id).copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col).set_index(date_col)
    if len(df) < 2 * period:
        period = max(2, len(df) // 4)
    res = seasonal_decompose(df[value_col].fillna(method="ffill"), period=period, extrapolate_trend="freq")
    return {
        "trend_first": float(res.trend.dropna().iloc[0]),
        "trend_last": float(res.trend.dropna().iloc[-1]),
        "seasonal_amplitude": float(res.seasonal.max() - res.seasonal.min()),
        "residual_std": float(res.resid.dropna().std()),
        "period_used": period,
    }
