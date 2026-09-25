from pathlib import Path
import json
import pandas as pd
from .inventory import recommend


class RetailService:
    """Serve precomputed daily forecasts; serving never unpickles a model."""
    def __init__(self, root):
        root = Path(root)
        self.meta = json.loads((root / "reports/metrics.json").read_text())
        self.sales = pd.read_csv(root / "artifacts/daily_sales.csv", dtype={"sku": str})
        self.pred = pd.read_csv(root / "artifacts/forecasts.csv", dtype={"sku": str})
        self.skus = sorted(self.pred.sku.unique())

    def forecast(self, sku, horizon=7):
        if sku not in self.skus:
            raise KeyError(sku)
        if not 1 <= horizon <= 28:
            raise ValueError("Horizon must be 1..28")
        rows = self.pred[self.pred.sku == sku].sort_values("date").head(horizon)
        return {"sku": sku, "model": self.meta["selected_model"],
                "origin": self.meta["trained_through"], "data_source": self.meta["data_source"],
                "forecasts": rows[["date", "prediction", "horizon"]].to_dict("records")}

    def order(self, sku, **kwargs):
        rows = self.forecast(sku, 28)["forecasts"]
        return {"sku": sku, "origin": self.meta["trained_through"],
                **recommend([r["prediction"] for r in rows], **kwargs)}
