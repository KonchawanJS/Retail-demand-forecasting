# Publish your repository

The provided project has not been pushed to any GitHub account. Create a new empty repository named `retail-demand-forecasting` in your account, without an automatically generated README/license/gitignore, then run these commands from this project directory:

```bash
git init
git add .
git commit -m "Build end-to-end retail forecasting and inventory planner"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/retail-demand-forecasting.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your account name and use GitHub's normal sign-in flow. Never paste access tokens into source files. The `.gitignore` excludes local datasets, trained models, SQLite files, credentials and environments. Review `git status` before committing.

## Repository presentation

Suggested description: `End-to-end retail forecasting and inventory planning with temporal backtesting, FastAPI, Streamlit and Docker.`

Suggested topics: `machine-learning`, `data-science`, `forecasting`, `inventory-management`, `fastapi`, `streamlit`, `python`, `portfolio`.

Before sharing with recruiters:

1. Replace the LICENSE copyright holder and add your name/contact to the README if desired.
2. Read and explain the data splits, feature availability and inventory assumptions.
3. Run a real-data experiment, inspect difficult products and document what you learn. Keep synthetic and real-data results clearly separate.
4. Add an actual dashboard screenshot and a 2–3 minute demo recording or deployed demo URL when available.
5. Wait for the GitHub Actions workflow to finish; a local test pass does not imply a GitHub CI pass.
6. Write honest resume metrics. Say “on a historical holdout” or “in a simulation”; do not claim production savings.

## Optional deployment

For a reproducible local demo, use `docker compose up --build`. For a VM you control with Docker, the same services can be started there after configuring networking and access. This package does not provision hosting or publish a public URL. A public deployment needs TLS, an access policy, operational logs and immutable artifact rollout. Keep private customer data off a public portfolio demo.
