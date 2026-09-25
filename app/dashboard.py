"""Streamlit UI uses the same service layer as the REST API."""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd
import streamlit as st

from retail.service import RetailService

st.set_page_config(page_title="Stockwise | Retail Planning", page_icon="📦", layout="wide")
st.markdown("""<style>
[data-testid="stAppViewContainer"] {background: #f5f7fb;}
[data-testid="stMetric"] {background: white; border: 1px solid #dce4ee;
 border-radius: 12px; padding: 18px;}
h1 {letter-spacing: -1px; color: #16324f;}
</style>""", unsafe_allow_html=True)
root = Path(os.getenv("RETAIL_ROOT", str(PROJECT_ROOT)))

required_files = [
    root / "reports" / "metrics.json",
    root / "artifacts" / "daily_sales.csv",
    root / "artifacts" / "forecasts.csv",
]

if not all(file.exists() for file in required_files):
    with st.spinner(
        "กำลังเตรียมข้อมูลและสร้าง Demand Forecast ครั้งแรก "
        "อาจใช้เวลาสักครู่..."
    ):
        result = subprocess.run(
            [sys.executable, "-m", "retail.cli", "demo"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )

    if result.returncode != 0:
        st.error("ไม่สามารถสร้างข้อมูล Forecast ได้")
        st.code(result.stderr)
        st.stop()

    # ตรวจอีกครั้งหลัง pipeline ทำงาน
    missing_files = [
        str(file.relative_to(root))
        for file in required_files
        if not file.exists()
    ]

    if missing_files:
        st.error("Pipeline ทำงานแล้ว แต่ยังไม่พบไฟล์ที่จำเป็น")
        st.code("\n".join(missing_files))
        st.stop()

    st.success("สร้าง Demand Forecast สำเร็จ")
st.caption("STOCKWISE  /  FORECAST → PLAN → EVALUATE")
st.title("Retail demand & replenishment")
st.write("พยากรณ์ยอดขายและวางแผนสั่งซื้อ พร้อมตรวจสอบผลและสมมติฐาน")
service = RetailService(root)
meta = service.meta
if meta["data_source"] == "synthetic_demo":
    st.warning("DEMO DATA · ข้อมูลจำลองสำหรับสาธิต ผลลัพธ์นี้ไม่ใช่ผลการดำเนินงานของธุรกิจจริง")
else:
    st.info("USER DATA · ยอดขายที่สังเกตได้อาจต่ำกว่าความต้องการเมื่อสินค้าขาด")
st.caption(f"Forecast origin: {meta['trained_through']} · Model: {meta['selected_model']} · 28-day maximum horizon · Historical replay; not today's live sales")
with st.sidebar:
    st.header("Planning controls")
    sku = st.selectbox("สินค้า / SKU", service.skus)
    horizon = st.slider("ช่วงแสดงผลพยากรณ์ (วัน)", 1, 28, 14)
    st.subheader("Inventory assumptions")
    on_hand = st.number_input("คงเหลือ / On hand", min_value=0.0, value=150.0, step=10.0)
    on_order = st.number_input("สินค้ารอรับ / On order", min_value=0.0, value=0.0)
    backorders = st.number_input("ยอดค้างส่ง / Backorders", min_value=0.0, value=0.0)
    lead_days = st.slider("เวลารอสินค้า / Lead days", 0, 14, 3)
    review_days = st.slider("รอบตรวจสต็อก / Review days", 1, 14, 7)
    safety_days = st.slider("จำนวนวันสำรอง / Safety days", 0.0, 7.0, 2.0, 0.5)
    pack_size = st.number_input("ขนาดแพ็ก / Pack size", min_value=1, value=1)
    min_order = st.number_input("ขั้นต่ำ / Minimum order", min_value=0, value=0)
plan = service.order(sku, on_hand=on_hand, on_order=on_order, backorders=backorders,
                     lead_days=lead_days, review_days=review_days, safety_days=safety_days,
                     pack_size=pack_size, min_order=min_order)
future = pd.DataFrame(service.forecast(sku, horizon)["forecasts"])
a, b, c, d = st.columns(4)
a.metric(f"Forecast · {horizon} days", f"{future.prediction.sum():,.0f}", "units", delta_color="off")
b.metric("Recommended order", f"{plan['recommended_order']:,}", "units", delta_color="off")
c.metric("Protection period", f"{plan['protection_days']}", "days", delta_color="off")
d.metric("Safety stock", f"{plan['safety_stock']:,.0f}", "units", delta_color="off")
tab1, tab2, tab3 = st.tabs(["Forecast & order", "Model evaluation", "Inventory scenarios"])
with tab1:
    st.subheader(f"Sales outlook · {sku}")
    history = service.sales[service.sales.sku == sku].tail(60).set_index("date")[["quantity"]]
    chart = history.rename(columns={"quantity": "Observed sales"}).join(
        future.set_index("date")[["prediction"]].rename(columns={"prediction": "Forecast"}), how="outer")
    chart.index = pd.to_datetime(chart.index)
    st.line_chart(chart, color=["#16324f", "#008f7a"])
    st.subheader("Why this order?")
    st.write(f"Expected sales over {plan['protection_days']} days: **{plan['expected_sales']:,.1f}** + "
             f"safety stock **{plan['safety_stock']:,.1f}** − inventory position "
             f"**{plan['inventory_position']:,.1f}**; then apply minimum order and pack size.")
    st.caption("สต็อกสำรองใช้จำนวนวันเผื่อ ไม่ใช่การรับประกันระดับบริการ และสมมติว่าสินค้ารอรับจะมาถึงในช่วงวางแผน")
    st.dataframe(future, hide_index=True, width="stretch")
    st.download_button("Download forecast CSV", future.to_csv(index=False), f"{sku}-forecast.csv", "text/csv")
with tab2:
    st.subheader("Validation selects; holdout evaluates")
    scores = pd.DataFrame(meta["scores"])
    scores["wape_percent"] = scores.wape * 100
    st.dataframe(scores[["split", "model", "mae", "wape_percent", "bias", "n"]], hide_index=True, width="stretch")
    st.caption("Two 28-day rolling validation windows choose the model. The final 28-day holdout is never used to select it. Lower MAE/WAPE is better.")
    scored = pd.read_csv(root / "reports/backtest_predictions.csv", dtype={"sku": str})
    g = scored[(scored.sku == sku) & (scored.split == "holdout")]
    comparison = g.pivot(index="date", columns="model", values="prediction")
    comparison["Observed sales"] = g.drop_duplicates("date").set_index("date").quantity
    comparison.index = pd.to_datetime(comparison.index)
    st.line_chart(comparison)
with tab3:
    st.subheader("One-cycle inventory simulation")
    st.write("เปรียบเทียบสองวิธีพยากรณ์ด้วยสต็อกเริ่มต้นและเงื่อนไขเดียวกัน ใช้ยอดขาย holdout เป็นตัวแทนความต้องการ")
    simulations = pd.read_csv(root / "reports/inventory_simulation.csv", dtype={"sku": str})
    st.dataframe(simulations[simulations.sku == sku], hide_index=True, width="stretch")
    st.caption("Fixed offline scenario: 10 days, initial stock = 5 × trailing daily mean, lead time = 3 days, review = 7 days, safety = 2 days, holding = 0.05/unit/day. Shortage penalties = 1, 2, 5 currency units. Sidebar controls affect the live recommendation only. This is not measured savings or a full inventory simulator.")
with st.expander("Data & limitations"):
    st.json({k: meta[k] for k in ["data_source", "rows", "skus", "data_sha256", "limitations"]})
