import numpy as np
import pandas as pd
import pytest
from retail.data import synthetic_sales, validate_daily
from retail.model import origin_features, training_matrix, fit_model, forecast
from retail.inventory import recommend, simulate_cycle
from retail.evaluate import metrics


def test_reject_ambiguous_daily_data():
    df = synthetic_sales(days=40, skus=1)
    for invalid in [pd.concat([df, df.head(1)]), df.iloc[1:].drop(index=[5]),
                    df.assign(quantity=-1), df.assign(quantity=np.inf)]:
        with pytest.raises(ValueError):
            validate_daily(invalid)


def test_future_changes_do_not_change_past_features():
    df = synthetic_sales(days=90, skus=2)
    cutoff = pd.Timestamp("2024-02-15")
    changed = df.copy()
    changed.loc[changed.date > cutoff, "quantity"] = 999999
    mapping = {"SKU-001": 0, "SKU-002": 1}
    first = origin_features(df, mapping)
    second = origin_features(changed, mapping)
    pd.testing.assert_frame_equal(first[first.date <= cutoff], second[second.date <= cutoff])


def test_training_labels_stay_before_cutoff():
    # Monotonic labels make any out-of-cutoff target immediately visible.
    dates = pd.date_range("2024-01-01", periods=70)
    df = pd.DataFrame({"date": dates, "sku": "A", "quantity": np.arange(70)})
    x, y = training_matrix(df.iloc[:50], {"A": 0})
    assert y.max() == 49
    assert (y.to_numpy() == x.recent_1.to_numpy() + x.horizon.to_numpy()).all()


def test_forecast_is_nonnegative_and_baseline_repeats_known_week():
    df = synthetic_sales(days=80, skus=2)
    fitted = fit_model(df)
    predicted = forecast(df, fitted, 28)
    assert len(predicted) == 56
    assert predicted.prediction.ge(0).all()
    assert predicted.date.min() > df.date.max()
    baseline = forecast(df, fitted, 14, "seasonal_naive")
    for sku, group in baseline.groupby("sku"):
        expected = np.tile(df[df.sku == sku].quantity.tail(7).to_numpy(), 2)
        np.testing.assert_array_equal(group.prediction, expected)


def test_order_accounts_for_incoming_backorders_and_rounding():
    result = recommend([10]*28, on_hand=20, on_order=15, backorders=5,
                       lead_days=3, review_days=7, safety_days=2, pack_size=12)
    assert result["inventory_position"] == 30
    assert result["target_stock"] == 120
    assert result["recommended_order"] == 96
    assert recommend([10]*28, on_hand=1000, min_order=100)["recommended_order"] == 0
    assert recommend([10]*28, on_hand=119, min_order=50, pack_size=12)["recommended_order"] == 60


@pytest.mark.parametrize("kwargs", [dict(lead_days=25), dict(on_hand=-1),
                                      dict(pack_size=0), dict(safety_days=float("nan"))])
def test_invalid_inventory_inputs(kwargs):
    with pytest.raises(ValueError):
        recommend([10]*28, **kwargs)


def test_arrival_timing_and_lost_sales():
    result = simulate_cycle([10, 10, 10], 30, initial_stock=0, lead_days=1,
                            holding_cost=0, shortage_cost=2)
    assert result["lost_units"] == 10
    assert result["ending_stock"] == 10
    assert result["total_cost"] == 20


def test_zero_actuals_wape_is_undefined():
    result = metrics(pd.DataFrame({"quantity": [0, 0], "prediction": [1, 2]}))
    assert result["wape"] is None
    assert result["mae"] == 1.5
