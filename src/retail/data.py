"""Explicit input contracts; SQLite is the local analytical store."""
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd


def synthetic_sales(days=420, skus=20, seed=42):
    """Reproducible demonstration data, NOT real business evidence."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=days)
    rows = []
    for i in range(skus):
        base = rng.uniform(12, 65)
        for t, date in enumerate(dates):
            weekly = [0.83, 0.87, 0.93, 1.0, 1.17, 1.40, 1.24][date.dayofweek]
            seasonal = 1 + 0.14 * np.sin(2 * np.pi * t / 90 + i / 3)
            mean = base * weekly * seasonal * (1 + 0.0006 * t)
            qty = int(rng.poisson(mean))
            rows.append((date, f"SKU-{i+1:03d}", qty))
    return pd.DataFrame(rows, columns=["date", "sku", "quantity"])


def validate_daily(frame):
    required = {"date", "sku", "quantity"}
    if not required.issubset(frame.columns):
        raise ValueError(f"CSV must contain columns {sorted(required)}")
    df = frame[["date", "sku", "quantity"]].copy()
    if df.empty or df.isna().any().any():
        raise ValueError("Input is empty or contains missing required values")
    df["date"] = pd.to_datetime(df.date, errors="raise").dt.normalize()
    df["sku"] = df.sku.astype(str).str.strip()
    df["quantity"] = pd.to_numeric(df.quantity, errors="raise")
    if (df.sku == "").any() or not np.isfinite(df.quantity).all() or (df.quantity < 0).any():
        raise ValueError("SKU must be nonempty and quantity must be finite and nonnegative")
    if df.duplicated(["date", "sku"]).any():
        raise ValueError("Duplicate date/SKU rows; aggregate transactions explicitly first")
    # Missing observations are not silently interpreted as zero demand.
    start, end = df.date.min(), df.date.max()
    expected = len(pd.date_range(start, end))
    sizes = df.groupby("sku").size()
    if not (sizes == expected).all():
        raise ValueError("All SKUs must have the same complete daily calendar; fill known zero-sale days explicitly")
    return df.sort_values(["sku", "date"]).reset_index(drop=True)


def load_daily(path):
    return validate_daily(pd.read_csv(path, dtype={"sku": str}))


def write_sqlite(df, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        df.assign(date=df.date.dt.strftime("%Y-%m-%d")).to_sql(
            "daily_sales", conn, if_exists="replace", index=False
        )
        conn.execute("CREATE UNIQUE INDEX sales_key ON daily_sales(sku, date)")
        summary = pd.read_sql_query(
            "SELECT sku, COUNT(*) AS days, SUM(quantity) AS units, "
            "AVG(quantity) AS daily_mean FROM daily_sales GROUP BY sku ORDER BY units DESC", conn
        )
    return summary


def import_uci(path, output, top_n=20):
    """Convert UCI Online Retail / II. Top SKU selection uses first 90 days only."""
    sheets = pd.read_excel(path, sheet_name=None)
    raw = pd.concat(sheets.values(), ignore_index=True)
    raw = raw.rename(columns={"Invoice": "InvoiceNo", "Price": "UnitPrice"})
    required = {"InvoiceNo", "InvoiceDate", "StockCode", "Quantity", "UnitPrice"}
    if not required.issubset(raw):
        raise ValueError(f"Workbook needs {sorted(required)}")
    qty = pd.to_numeric(raw.Quantity, errors="coerce")
    price = pd.to_numeric(raw.UnitPrice, errors="coerce")
    date = pd.to_datetime(raw.InvoiceDate, errors="coerce").dt.normalize()
    keep = (~raw.InvoiceNo.astype(str).str.upper().str.startswith("C") &
            qty.gt(0) & price.gt(0) & date.notna() & raw.StockCode.notna())
    clean = pd.DataFrame({"date": date[keep], "sku": raw.StockCode[keep].astype(str),
                          "quantity": qty[keep]})
    if clean.empty:
        raise ValueError("No valid positive sales transactions")
    start, end = clean.date.min(), clean.date.max()
    selected = (clean[clean.date < start + pd.Timedelta(days=90)]
                .groupby("sku").quantity.sum().nlargest(top_n).index)
    if selected.empty:
        raise ValueError("No products in initial selection window")
    daily = clean[clean.sku.isin(selected)].groupby(["date", "sku"]).quantity.sum()
    index = pd.MultiIndex.from_product([pd.date_range(start, end), selected], names=["date", "sku"])
    daily = validate_daily(daily.reindex(index, fill_value=0).reset_index())
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output, index=False)
    return {"source_rows": len(raw), "kept_rows": int(keep.sum()), "skus": len(selected),
            "days": (end-start).days+1, "zero_fill_assumption": True,
            "note": "Positive gross sales only. Missing transaction days assumed zero sales, not proven zero demand. Returns excluded; no stock availability data."}
