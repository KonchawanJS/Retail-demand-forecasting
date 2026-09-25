from pathlib import Path
import hashlib
import json
import platform
import joblib
import pandas as pd
import sklearn
from .data import synthetic_sales, load_daily, validate_daily, write_sqlite
from .evaluate import backtest, inventory_scenarios
from .model import fit_model, forecast


def run_pipeline(root, csv_path=None):
    root = Path(root)
    artifacts, reports = root / "artifacts", root / "reports"
    artifacts.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    df = load_daily(csv_path) if csv_path else validate_daily(synthetic_sales())
    source = "user_csv" if csv_path else "synthetic_demo"
    summary = write_sqlite(df, artifacts / "sales.sqlite")
    summary.to_csv(reports / "sales_summary.csv", index=False)
    df.to_csv(artifacts / "daily_sales.csv", index=False)
    print("Running temporal validation and held-out evaluation...", flush=True)
    scored, scores, per_sku, per_horizon, winner = backtest(df)
    scored.to_csv(reports / "backtest_predictions.csv", index=False)
    pd.DataFrame(per_sku).to_csv(reports / "metrics_by_sku.csv", index=False)
    pd.DataFrame(per_horizon).to_csv(reports / "metrics_by_horizon.csv", index=False)
    inventory_scenarios(df, scored).to_csv(reports / "inventory_simulation.csv", index=False)
    fitted = fit_model(df)
    metadata = {"data_source": source, "selected_model": winner,
                "selection_rule": "Lowest aggregate validation MAE; holdout excluded from selection",
                "trained_through": str(df.date.max().date()), "skus": int(df.sku.nunique()),
                "rows": len(df), "horizon": 28, "seed": 42,
                "data_sha256": hashlib.sha256((artifacts / "daily_sales.csv").read_bytes()).hexdigest(),
                "python_version": platform.python_version(), "sklearn_version": sklearn.__version__,
                "scores": scores,
                "limitations": ["Observed sales are a proxy for demand", "No stockout correction",
                                "Inventory costs and stock are hypothetical", "No future promotions or prices"]}
    joblib.dump({**fitted, "metadata": metadata}, artifacts / "model.joblib")
    (reports / "metrics.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    pred = forecast(df, fitted, method=winner)
    pred["data_sha256"] = metadata["data_sha256"]
    pred.to_csv(artifacts / "forecasts.csv", index=False)
    create_plot(scored, reports / "holdout_forecast.png")
    print(json.dumps(metadata, indent=2), flush=True)
    return metadata


def create_plot(scored, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sku = sorted(scored.sku.unique())[0]
    g = scored[(scored.sku == sku) & (scored.split == "holdout")]
    fig, ax = plt.subplots(figsize=(10, 4))
    actual = g.drop_duplicates("date").sort_values("date")
    ax.plot(actual.date, actual.quantity, label="Observed sales", color="#162f49", linewidth=2)
    for method, rows in g.groupby("model"):
        ax.plot(rows.date, rows.prediction, label=method, linestyle="--")
    ax.set(title=f"Untouched 28-day holdout | {sku}", ylabel="Units", xlabel="Date")
    ax.legend(frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
