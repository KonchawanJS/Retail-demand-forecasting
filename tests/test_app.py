import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from retail.api import create_app
from retail.data import synthetic_sales
from retail.cli import monitor


@pytest.fixture
def serving_root(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "reports").mkdir()
    sales = synthetic_sales(days=60, skus=1)
    sales.to_csv(tmp_path / "artifacts/daily_sales.csv", index=False)
    pred = pd.DataFrame({"date": pd.date_range(sales.date.max()+pd.Timedelta(days=1), periods=28),
                         "sku": "SKU-001", "prediction": 10.0, "horizon": range(1, 29)})
    pred.to_csv(tmp_path / "artifacts/forecasts.csv", index=False)
    meta = {"selected_model": "ml", "trained_through": str(sales.date.max().date()),
            "data_source": "synthetic_demo"}
    (tmp_path / "reports/metrics.json").write_text(json.dumps(meta))
    return tmp_path


def test_api_contract_and_errors(serving_root):
    with TestClient(create_app(serving_root)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/products").json()["skus"] == ["SKU-001"]
        forecast = client.get("/forecast/SKU-001?horizon=14").json()
        assert len(forecast["forecasts"]) == 14
        assert client.get("/forecast/unknown").status_code == 404
        assert client.get("/forecast/SKU-001?horizon=29").status_code == 422
        assert client.post("/inventory/recommend", json={"sku": "SKU-001"}).json()["recommended_order"] == 70
        for body in [{"sku": "SKU-001", "on_hand": -1},
                     {"sku": "SKU-001", "lead_days": 25, "review_days": 7},
                     {"sku": "SKU-001", "unknown": 1}]:
            assert client.post("/inventory/recommend", json=body).status_code == 422
        assert client.post("/inventory/recommend", json={"sku": "missing"}).status_code == 404


def test_monitor_matches_dates_and_reports_partial_coverage(serving_root):
    path = serving_root / "artifacts/forecasts.csv"
    actuals = pd.read_csv(path).head(7).rename(columns={"prediction": "quantity"})
    actuals.to_csv(serving_root / "actuals.csv", index=False)
    result = monitor(path, serving_root / "actuals.csv", serving_root / "monitoring.json")
    assert result["coverage"] == 0.25
    assert result["mae"] == 0
