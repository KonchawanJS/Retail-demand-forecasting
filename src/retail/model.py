"""Direct multi-horizon model: no actuals inside the forecast window are features."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

MAX_HORIZON = 28
FEATURES = ["sku_code", "recent_1", "recent_7", "recent_14", "mean_7", "mean_28",
            "std_28", "horizon", "target_dow", "target_month"]


def origin_features(history, sku_map):
    frames = []
    for sku, part in history.groupby("sku", sort=True):
        g = part.sort_values("date").copy()
        q = g.quantity
        g["sku_code"] = sku_map[sku]
        # An origin is the END of an observed day; quantity on that day is known.
        g["recent_1"] = q
        g["recent_7"] = q.shift(6)
        g["recent_14"] = q.shift(13)
        g["mean_7"] = q.rolling(7).mean()
        g["mean_28"] = q.rolling(28).mean()
        g["std_28"] = q.rolling(28).std(ddof=0)
        frames.append(g)
    return pd.concat(frames, ignore_index=True)


def training_matrix(history, sku_map, max_horizon=MAX_HORIZON):
    base = origin_features(history, sku_map)
    rows = []
    for h in range(1, max_horizon + 1):
        block = base.copy()
        block["target"] = base.groupby("sku", sort=False).quantity.shift(-h)
        block["horizon"] = h
        target_date = block.date + pd.Timedelta(days=h)
        block["target_dow"] = target_date.dt.dayofweek
        block["target_month"] = target_date.dt.month
        rows.append(block.dropna(subset=FEATURES + ["target"]))
    long = pd.concat(rows, ignore_index=True)
    if long.empty or long.target.sum() <= 0:
        raise ValueError("Need sufficient history and positive sales for model training")
    return long[FEATURES], long.target


def fit_model(history):
    sku_map = {sku: i for i, sku in enumerate(sorted(history.sku.unique()))}
    if len(sku_map) > 255:
        raise ValueError("This portfolio model supports up to 255 SKUs")
    x, y = training_matrix(history, sku_map)
    model = HistGradientBoostingRegressor(
        loss="poisson", max_iter=90, max_leaf_nodes=15, learning_rate=0.08,
        l2_regularization=2.0, categorical_features=[0],
        early_stopping=False, random_state=42
    )
    with threadpool_limits(limits=1):
        model.fit(x, y)
    return {"model": model, "sku_map": sku_map}


def forecast(history, fitted, horizon=MAX_HORIZON, method="ml"):
    if not 1 <= horizon <= MAX_HORIZON:
        raise ValueError(f"Horizon must be between 1 and {MAX_HORIZON}")
    if method not in {"ml", "seasonal_naive"}:
        raise ValueError("Unknown forecast method")
    cutoff = history.date.max()
    frames = []
    if method == "ml":
        latest = origin_features(history, fitted["sku_map"]).groupby("sku").tail(1)
        for h in range(1, horizon + 1):
            block = latest.copy()
            block["date"] = cutoff + pd.Timedelta(days=h)
            block["horizon"] = h
            block["target_dow"] = block.date.dt.dayofweek
            block["target_month"] = block.date.dt.month
            with threadpool_limits(limits=1):
                block["prediction"] = np.maximum(0, fitted["model"].predict(block[FEATURES]))
            frames.append(block[["date", "sku", "prediction", "horizon"]])
    else:
        for sku, part in history.groupby("sku"):
            last_week = part.sort_values("date").quantity.tail(7).to_numpy()
            if len(last_week) < 7:
                raise ValueError("Seasonal baseline requires seven observations")
            frames.append(pd.DataFrame({"date": pd.date_range(cutoff + pd.Timedelta(days=1), periods=horizon),
                                        "sku": sku, "prediction": np.resize(last_week, horizon),
                                        "horizon": np.arange(1, horizon+1)}))
    result = pd.concat(frames, ignore_index=True)
    result["origin"] = cutoff
    result["model"] = method
    return result.sort_values(["sku", "date"]).reset_index(drop=True)
