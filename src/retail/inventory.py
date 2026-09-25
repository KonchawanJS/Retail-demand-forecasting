"""Periodic-review order-up-to policy with user supplied assumptions."""
import math


def recommend(predictions, *, on_hand=50, on_order=0, backorders=0,
              lead_days=3, review_days=7, safety_days=2.0, pack_size=1, min_order=0):
    numbers = [on_hand, on_order, backorders, lead_days, review_days, safety_days, pack_size, min_order]
    if any(not math.isfinite(float(v)) or v < 0 for v in numbers):
        raise ValueError("Inventory inputs must be finite and nonnegative")
    if any(int(v) != v for v in [lead_days, review_days, pack_size, min_order]):
        raise ValueError("Days, pack size and minimum order must be integers")
    if review_days < 1 or pack_size < 1:
        raise ValueError("Review days and pack size must be positive")
    protection = lead_days + review_days
    if protection > len(predictions):
        raise ValueError("Forecast does not cover lead time plus review interval")
    window = [float(v) for v in predictions[:protection]]
    if any(not math.isfinite(v) or v < 0 for v in window):
        raise ValueError("Predictions must be finite and nonnegative")
    expected = sum(window)
    safety = expected / protection * safety_days
    position = on_hand + on_order - backorders
    raw = max(0.0, expected + safety - position)
    order = math.ceil(max(raw, min_order) / pack_size) * pack_size if raw > 0 else 0
    return {"protection_days": protection, "expected_sales": round(expected, 2),
            "safety_stock": round(safety, 2), "inventory_position": position,
            "target_stock": round(expected + safety, 2), "recommended_order": order,
            "assumption": "Safety stock is a days-of-cover heuristic, not a calibrated service-level guarantee. Incoming stock is assumed available within the protection period."}


def simulate_cycle(actuals, order, *, initial_stock, lead_days, holding_cost=0.05, shortage_cost=2.0):
    """Single review-cycle lost-sales scenario. Arrival at start of lead_days+1.

    Costs are hypothetical currency units. No carry-over orders or replenishment
    beyond this one cycle; actual demand is approximated by observed sales.
    """
    stock, lost, sold, holding = float(initial_stock), 0.0, 0.0, 0.0
    for day, demand in enumerate(actuals):
        if day == lead_days:
            stock += order
        filled = min(stock, float(demand))
        sold += filled
        lost += float(demand) - filled
        stock -= filled
        holding += stock * holding_cost
    return {"order": int(order), "lost_units": lost, "ending_stock": stock,
            "fill_rate": sold / (sold + lost) if sold + lost else 1.0,
            "holding_cost": holding, "shortage_cost": lost * shortage_cost,
            "total_cost": holding + lost * shortage_cost}
