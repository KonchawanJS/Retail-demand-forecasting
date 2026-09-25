# Methodology and assumptions

## Forecast origin and leakage controls

An origin is the end of a fully observed day `t`. Recent sales and rolling statistics include day `t`; targets begin on `t+1`. Features are product category code, sales on `t`, `t-6`, `t-13`, mean over the latest 7/28 observed days, population standard deviation over 28 days, horizon, target weekday and target month.

A single pooled gradient boosting model learns direct targets for horizons 1–28. Training pairs only exist when `origin + horizon <= training cutoff`. Inference builds all horizons from the same last observed history; no actuals from inside the future window enter the features. Product IDs use categorical treatment, not a numeric distance. Features deliberately exclude unavailable future promotions/prices.

## Temporal splits

With last date `T`:

| Window | Training ends | Scoring dates |
|---|---|---|
| Validation 1 | T−84 | T−83 through T−56 |
| Validation 2 | T−56 | T−55 through T−28 |
| Holdout | T−28 | T−27 through T |

The training window expands. Validation 2 can use past validation 1 observations because those are known at its origin. Aggregate validation MAE selects either ML or seasonal naive. The two model holdout results are reported for transparency, but never determine selection. A final model refits all available history for future forecasts. Every SKU has equal row weight; no revenue weighting is implied.

The seasonal baseline repeats the latest seven observed days. It does not read previous-week actuals that fall inside the forecast horizon. The minimum 180-day input contract leaves at least 96 days before the first validation origin.

## Metrics

MAE = mean absolute forecast error, in units. WAPE = sum absolute error / sum absolute actuals, pooled across the relevant rows; it is undefined (`null`) when all actuals are zero. Bias = mean(prediction − actual); negative means underforecasting. Breakdown reports identify products and lead horizons hidden by aggregate scores.

## Inventory policy

Protection period = lead time + review interval.

Target stock = sum of forecasts over protection period + safety stock.

Safety stock = forecast average daily sales over protection period × user-selected safety days.

Inventory position = on hand + on order − backorders.

Order = max(0, target stock − inventory position), then minimum-order and pack-size rounding if any order is needed. A minimum order does not force an order when stock is already sufficient. Safety days are a heuristic, not a 95% service-level calculation or prediction interval.

The planner assumes incoming stock will be available within the planning period. Without receipt dates it cannot ensure stock is sufficient before each arrival. Backorders reduce the inventory position but there is no detailed fulfillment queue. The response is a decision aid, not an automatic purchase order.

## Inventory experiment

The offline comparison is one independent 10-day cycle per SKU at the holdout origin. Both forecasting approaches receive initial stock equal to five times the trailing 28-day daily mean. Both use lead time 3 days, review interval 7 days, safety cover 2 days and a single order. The order arrives at the start of day 4; unmet demand before arrival is lost and is not backordered. Holding costs accrue on closing inventory each day. Forecasts come only from that origin.

Costs are hypothetical: holding 0.05 currency units/unit/day and lost-sales penalties of 1, 2 or 5 currency units/unit. There are no ordering fees, shelf-life effects, purchase costs, terminal inventory valuation or supplier constraints. The simulation reports sensitivity and fill rate, not profit or measured savings. Observed sales proxy demand; unknown stockouts can invalidate this assumption. Sidebar controls are separate from this fixed offline experiment.

## Data limitations

UCI conversion excludes cancellations and nonpositive prices/quantities, thus targets gross positive sales rather than net sales after returns. Exact duplicate-looking invoice lines are retained because no reliable unique line ID is supplied. Product selection is based only on the initial 90 days; selection by all-time volume would expose future information. Absent transaction days are filled with zero observed sales, which may also indicate missing data, closures, delisting or stockouts. The final day of a transactional extract can be partial. Inspect those issues before applying results. The generic daily CSV loader rejects missing days.

## Operations

The project is batch-first. Re-run the pipeline on a new complete data snapshot, inspect validation/holdout results, then restart serving against the generated files. Artifact writes are not atomic releases; do not train into the directory currently serving requests. Preserve old snapshots externally when building a production deployment. Metadata records the dataset hash, Python and sklearn versions, cutoff and source type. Python dependencies are locked for the tested environment. Request logs report status and latency; actual-sales monitoring is a separate CLI step.
