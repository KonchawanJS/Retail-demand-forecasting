import pandas as pd
from retail.data import import_uci, load_daily


def test_uci_import_excludes_returns_and_uses_initial_selection_window(tmp_path):
    raw = pd.DataFrame({
        "Invoice": ["1", "2", "C3", "4", "5"],
        "InvoiceDate": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-04-10", "2024-04-10"],
        "StockCode": ["A", "A", "A", "A", "NEW"],
        "Quantity": [10, 5, -5, 3, 10000], "Price": [1]*5,
    })
    source, output = tmp_path / "retail.xlsx", tmp_path / "daily.csv"
    raw.to_excel(source, index=False)
    report = import_uci(source, output, top_n=1)
    df = load_daily(output)
    assert report["kept_rows"] == 4
    assert set(df.sku) == {"A"}
    assert df.quantity.sum() == 18
    assert len(df) == 101
