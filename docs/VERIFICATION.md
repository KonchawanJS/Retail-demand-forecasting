# Verification record

Executed during project creation on 2026-09-25 with Python 3.12.14 and scikit-learn 1.8.0; dependency versions are recorded in requirements-lock.txt.

| Check | Result |
|---|---|
| `python -m retail.cli demo` | Passed; 20 products, 420 days, complete backtests and final forecasts |
| `python -m ruff check .` | Passed |
| `python -m pytest -q` | 14 tests passed |
| `python scripts/verify_demo.py` | Passed; API serves generated artifacts, dashboard renders and handles SKU changes and 28-day protection |
| EDA notebook code cells | Executed successfully against demo SQLite/report outputs |
| UCI workbook importer | Tested using a representative miniature workbook with cancellations and a late-introduced product |
| Full real UCI dataset training | Not executed; default reports use synthetic data |
| Docker image / Compose | Not executed; Docker unavailable in the development environment |
| GitHub Actions | Workflow supplied; not run on GitHub before repository publication |
| Hosted deployment | Not performed |

The test environment emitted a non-failing Starlette deprecation notice for its httpx-based TestClient, and Streamlit's expected bare-context warning during AppTest. Neither prevented validation. No claims of measured business savings are made.
