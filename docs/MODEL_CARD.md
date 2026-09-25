# Model card

**Name:** Stockwise pooled direct sales forecaster v0.1.0  
**Intended use:** internship portfolio, historical retail forecasting experiments and explainable inventory scenarios.  
**Model:** scikit-learn HistGradientBoostingRegressor, Poisson loss, 90 iterations, 15 leaves, learning rate 0.08, L2 2.0, no internal early stopping; random seed 42. A seasonal-naive fallback is selected when it wins validation.  
**Training:** CPU, direct horizons 1–28, expanding temporal windows.  
**Default data:** deterministic synthetic counts, 20 products × 420 days.  
**Real-data support:** explicit UCI workbook importer and daily CSV contract; source licensing is documented separately.  
**Output:** nonnegative expected daily unit sales and rule-based order quantities.  
**Evaluation:** pooled MAE/WAPE/bias plus SKU/horizon breakdown, separate holdout, hypothetical one-cycle inventory experiment. See generated reports.  
**Not evaluated:** causal effects of ordering, supplier reliability, real-world profit, fairness across business segments, stockout-adjusted demand, calibrated uncertainty.  
**Known weaknesses:** systematic underforecasting on the default demo, long-tail/intermittent demand, product launches, structural change, missing promotional context and unconstrained-demand censoring. Only known SKUs are served.  
**Safety stock:** heuristic days of cover, not a probabilistic service commitment.  
**Privacy:** synthetic demo has no personal data; the UCI aggregate contains no customer identifiers.  
**Serving:** precomputed CSV forecasts. Model pickle is a local training artifact only and is never loaded by the API/dashboard.  
**Deployment limits:** no authentication, rate limiting, automated retraining, atomic model promotion or drift alerts; intended for local/private demos. Add operational controls before exposing business data publicly.
