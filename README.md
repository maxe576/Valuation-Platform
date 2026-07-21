# Valuation Platform

A professional equity-research and company-valuation platform for a
student-managed investment fund. It imports reported financials (SEC EDGAR),
builds forecasts, runs multiple valuation methods, blends them into a fair-value
range, and keeps a full audit trail of sources and analyst decisions.

> **Free-first & paper-research only.** The app runs with **zero API keys** in
> demo mode. It produces research and valuations; it does not place trades.

## Status

Built through **Phase 3** (see `ROADMAP.md`):

- ✅ Phase 0 — repo scaffold, config, logging, Streamlit shell
- ✅ Phase 1 — domain models, DB schema, repository, demo-data mode
- ✅ Phase 2 — DCF engine ported from the legacy Excel model + tests
- ✅ Phase 3 — SEC EDGAR client + statement normalization + quarterly/TTM
- ⬜ Phase 4+ — remaining valuation engines, dashboard, AI, persistence, exports

## Quick start (Windows, no venv activation needed)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app opens in **demo mode** by default — bundled fixture company, no network.
To use live SEC data, copy `.env.example` to `.env` and set `APP_MODE=live` plus
a descriptive `SEC_USER_AGENT`.

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests never require a paid API key; external services are mocked.

## Architecture

Core rule: **financial logic is separated from the UI.** Streamlit only renders;
every valuation engine is a pure, independently tested Python module. This keeps
the door open to swapping Streamlit for React/Next.js later without touching the
engines.

```
config/       settings, logging, metric mappings, lifecycle weights
models/       typed domain objects (with source + confidence metadata)
services/     SEC / FMP / FRED clients, repository, cache
processing/   normalization, quarterly/TTM, reconciliation, quality checks
valuation/    dcf, comps, justified_multiple, sotp, residual_income, reverse_dcf, blend
database/     schema.sql, policies.sql, migrations, seed_demo.sql
pages/        Streamlit pages (Phase 6)
components/   reusable UI widgets (Phase 6)
exports/      Excel / CSV / PDF (Phase 9)
tests/        unit + integration tests
```

## Data sources (priority order)

1. **SEC EDGAR** — source of truth for U.S. filings (free, no key)
2. Company investor-relations materials
3. Financial Modeling Prep (optional convenience; redistribution may need a license)
4. FRED (macro)
5. Damodaran industry datasets (reference only)
6. Internal analyst estimates
7. AI-assisted extraction — always `ai_extracted_pending` until analyst approval

Every material value stores its original source, XBRL tag, status, and confidence.

## Legacy DCF

This platform ports an existing Excel DCF (`NFLX Valuation.xlsx`, YCharts-driven).
See `ROADMAP.md` and `valuation/dcf.py` for what was preserved and what was fixed.
