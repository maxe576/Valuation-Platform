# Development Roadmap

Build order is the **fast vertical slice**: get a working DCF on real SEC data
early, then complete the valuation suite, then the dashboard, then hardening.

Legend: ✅ done · 🔨 in progress · ⬜ planned

| Phase | Goal | Status |
|------:|------|:------:|
| 0 | Scaffold: repo, config, logging, Streamlit shell | ✅ |
| 1 | Core architecture: models, DB schema, repository, **demo-data mode** | ✅ |
| 2 | DCF port: legacy Excel model → tested Python engine | ✅ |
| 3 | SEC EDGAR: ticker→CIK, Company Facts, normalization, quarterly/TTM | ✅ |
| 4 | Remaining engines: comps, justified multiple, SOTP, residual income, reverse DCF, blend | ✅ |
| 5 | Segment intelligence: aliases, reconciliation, FMP fallback, segment history | ✅ |
| 6 | Dashboard (MVP milestone): all research pages | ✅ |
| 7 | AI layer: structured package, Ollama/Gemini/offline, JSON validation, approval | ✅ |
| 8 | Persistence: SQLite (local) + Supabase (cloud) repositories, auth, append-only runs | ✅ |
| 9 | Exports + outcome tracking: Excel/CSV/memo, 3/6/12-mo accuracy | ✅ |
| 10 | Deployment: Streamlit Cloud + Supabase + Windows docs, secrets bootstrap & hygiene | ✅ |

**All 10 phases complete.** See `DEPLOYMENT.md` for running locally, with Supabase, or on Streamlit Cloud.

## Legacy DCF: what was ported, what was fixed

The source model is a 7-sheet Excel workbook (Instructions, Multiples, DCF,
WACC, IS, BS, CFS), 100% driven by the YCharts Excel add-in (`_xll.YCP`).

**Preserved**
- UFCF build: `EBIAT + D&A − CapEx − ΔNWC`, discounted at WACC
- 3-case switch logic (Conservative / Base / Optimistic) → mapped to bear/base/bull
- Enterprise → equity bridge → implied price → upside vs. current
- Exit-multiple terminal value and EV/EBITDA comps concept

**Fixed / added (flagged for analyst review)**
- Terminal value string hack `=C75*LEFT(EM,2)` replaced with a numeric multiple
- Added **perpetual-growth** terminal method alongside exit-multiple (§14 requires both)
- Added WACC-vs-g and WACC-vs-exit-multiple **sensitivity tables**
- Added warning engine (WACC ≤ g, terminal % of EV too high, etc.)
- Replaced YCharts inputs with SEC EDGAR (truth) + optional FMP/FRED

**Not yet transferred (tracked)**
- YCharts credit-rating→yield table for cost of debt (Phase 4 WACC builder;
  will use FRED credit spreads + Damodaran as free replacements)
- Live market beta (`market_beta_60_month`) — will compute from price history or
  use Damodaran industry beta as fallback
