"""Two rolling validation windows select a model; last window stays untouched."""
import pandas as pd
from .model import MAX_HORIZON, fit_model, forecast
from .inventory import recommend, simulate_cycle


def metrics(rows):
    error = (rows.quantity - rows.prediction).abs()
    denom = float(rows.quantity.abs().sum())
    return {"mae": float(error.mean()), "wape": float(error.sum()/denom) if denom else None,
            "bias": float((rows.prediction - rows.quantity).mean()), "n": len(rows)}


def backtest(df):
    end = df.date.max()
    if (end-df.date.min()).days + 1 < 180:
        raise ValueError("Need at least 180 daily observations per SKU for this split")
    predictions = []
    winner = None
    for fold, offset in enumerate([84, 56, 28], start=1):
        cutoff = end - pd.Timedelta(days=offset)
        history = df[df.date <= cutoff]
        model = fit_model(history)
        for method in ["ml", "seasonal_naive"]:
            pred = forecast(history, model, MAX_HORIZON, method)
            scored = pred.merge(df, on=["date", "sku"], validate="one_to_one")
            scored["fold"] = fold
            scored["split"] = "holdout" if fold == 3 else "validation"
            predictions.append(scored)
        if fold == 2:
            val = pd.concat(predictions, ignore_index=True)
            # MAE and aggregate WAPE yield same ordering on identical observations;
            # MAE remains defined when actual sales are all zero.
            winner = min(["ml", "seasonal_naive"], key=lambda m: metrics(val[val.model == m])["mae"])
    scored = pd.concat(predictions, ignore_index=True)
    summary = [{"split": split, "model": method, **metrics(g)}
               for (split, method), g in scored.groupby(["split", "model"])]
    per_sku = [{"split": split, "model": method, "sku": sku, **metrics(g)}
               for (split, method, sku), g in scored.groupby(["split", "model", "sku"])]
    per_horizon = [{"split": split, "model": method, "horizon": int(h), **metrics(g)}
                   for (split, method, h), g in scored.groupby(["split", "model", "horizon"])]
    return scored, summary, per_sku, per_horizon, winner


def inventory_scenarios(df, scored):
    output = []
    holdout = scored[scored.split == "holdout"]
    cutoff = holdout.origin.iloc[0]
    means = df[(df.date <= cutoff) & (df.date > cutoff-pd.Timedelta(days=28))].groupby("sku").quantity.mean()
    for (method, sku), g in holdout.groupby(["model", "sku"]):
        g = g.sort_values("date")
        initial = float(means[sku] * 5)
        for penalty in [1.0, 2.0, 5.0]:
            plan = recommend(g.prediction.tolist(), on_hand=initial)
            sim = simulate_cycle(g.quantity.head(10), plan["recommended_order"],
                                 initial_stock=initial, lead_days=3, shortage_cost=penalty)
            output.append({"model": method, "sku": sku, "shortage_penalty": penalty,
                           "initial_stock": initial, **sim})
    return pd.DataFrame(output)
