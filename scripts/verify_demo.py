"""Run after the pipeline; checks the dashboard and API against real artifacts."""
import os
from pathlib import Path
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from retail.api import create_app

root = Path(os.getenv("RETAIL_ROOT", "."))
with TestClient(create_app(root)) as client:
    assert client.get("/health").status_code == 200
    products = client.get("/products").json()["skus"]
    sku = products[0]
    assert len(client.get(f"/forecast/{sku}?horizon=28").json()["forecasts"]) == 28
    result = client.post("/inventory/recommend", json={"sku": sku, "pack_size": 12})
    assert result.status_code == 200
    assert result.json()["recommended_order"] % 12 == 0

dashboard = Path(__file__).resolve().parents[1] / "app/dashboard.py"
app = AppTest.from_file(str(dashboard), default_timeout=30).run()
assert not app.exception, str(app.exception)
if len(products) > 1:
    app.sidebar.selectbox[0].select(products[1]).run()
app.sidebar.slider[1].set_value(14).run()
app.sidebar.slider[2].set_value(14).run()
assert not app.exception, str(app.exception)
print("API and dashboard passed with generated artifacts, including maximum protection period.")
