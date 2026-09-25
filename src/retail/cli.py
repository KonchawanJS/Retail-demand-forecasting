import argparse
from pathlib import Path
import json
import pandas as pd
from .data import import_uci
from .pipeline import run_pipeline
from .evaluate import metrics


def monitor(forecast_path, actual_path, output):
    pred = pd.read_csv(forecast_path, dtype={"sku": str})
    actual = pd.read_csv(actual_path, dtype={"sku": str})
    for df in [pred, actual]:
        df["date"] = pd.to_datetime(df.date, errors="raise").dt.normalize()
        if df.duplicated(["date", "sku"]).any():
            raise ValueError("One forecast vintage and unique date/SKU actuals are required")
    actual["quantity"] = pd.to_numeric(actual.quantity, errors="raise")
    import numpy as np
    if not np.isfinite(actual.quantity).all() or actual.quantity.lt(0).any():
        raise ValueError("Actual quantities must be finite and nonnegative")
    joined = pred.merge(actual[["date", "sku", "quantity"]], on=["date", "sku"], validate="one_to_one")
    if joined.empty:
        raise ValueError("No overlapping forecast and actual dates")
    result = {"matched_rows": len(joined), "forecast_rows": len(pred),
              "coverage": len(joined)/len(pred), **metrics(joined)}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="Retail forecasting pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["demo", "train"]:
        p = sub.add_parser(name)
        p.add_argument("--root", default=".")
        if name == "train":
            p.add_argument("--csv", required=True)
    p = sub.add_parser("import-uci")
    p.add_argument("--input", required=True)
    p.add_argument("--output", default="data/processed/daily_sales.csv")
    p.add_argument("--top-n", type=int, default=20)
    p = sub.add_parser("monitor")
    p.add_argument("--forecasts", default="artifacts/forecasts.csv")
    p.add_argument("--actuals", required=True)
    p.add_argument("--output", default="reports/monitoring.json")
    args = parser.parse_args()
    if args.command in {"demo", "train"}:
        run_pipeline(args.root, getattr(args, "csv", None))
    elif args.command == "import-uci":
        if not 1 <= args.top_n <= 255:
            parser.error("--top-n must be 1..255")
        print(json.dumps(import_uci(args.input, args.output, args.top_n), indent=2))
    else:
        print(json.dumps(monitor(args.forecasts, args.actuals, args.output), indent=2))


if __name__ == "__main__":
    main()
