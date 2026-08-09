"""Screener universe: the set of companies (with metrics) to score.

Two sources:
  * SEED — a curated set of large caps with approximate metrics, so the screener
    works instantly (demo mode, or before the live pipeline has run). Clearly
    illustrative, not official data.
  * LIVE — built from SEC bulk data (frames API) + prices; wired in a later step
    via ``screener.universe_builder`` and cached in Supabase.

Metric units follow models.strategy conventions: growth/margin in %, multiples as
ratios, market_cap in $B.
"""
from __future__ import annotations

from config.settings import SETTINGS

# key: ticker → metrics. Approximate, illustrative figures.
_SEED: list[dict] = [
    {"ticker": "NVDA", "name": "NVIDIA", "sector": "Semiconductors",
     "price": 128.0, "market_cap": 3150.0, "revenue_growth": 94, "ebit_margin": 62,
     "eps_growth": 120, "fcf_growth": 90, "ev_ebitda": 34, "ps": 28, "pe": 55, "peg": 1.1},
    {"ticker": "META", "name": "Meta Platforms", "sector": "Interactive Media",
     "price": 585.0, "market_cap": 1300.0, "revenue_growth": 22, "ebit_margin": 42,
     "eps_growth": 60, "fcf_growth": 25, "ev_ebitda": 15, "ps": 9, "pe": 26, "peg": 1.0},
    {"ticker": "GOOGL", "name": "Alphabet", "sector": "Interactive Media",
     "price": 178.0, "market_cap": 2100.0, "revenue_growth": 14, "ebit_margin": 32,
     "eps_growth": 30, "fcf_growth": 22, "ev_ebitda": 16, "ps": 6.5, "pe": 24, "peg": 1.3},
    {"ticker": "MSFT", "name": "Microsoft", "sector": "Software",
     "price": 418.6, "market_cap": 3100.0, "revenue_growth": 16, "ebit_margin": 45,
     "eps_growth": 20, "fcf_growth": 18, "ev_ebitda": 24, "ps": 13, "pe": 34, "peg": 2.1},
    {"ticker": "AAPL", "name": "Apple", "sector": "Hardware",
     "price": 227.0, "market_cap": 3450.0, "revenue_growth": 6, "ebit_margin": 31,
     "eps_growth": 10, "fcf_growth": 9, "ev_ebitda": 26, "ps": 9, "pe": 34, "peg": 3.0},
    {"ticker": "AMZN", "name": "Amazon", "sector": "Consumer Discretionary",
     "price": 185.0, "market_cap": 1930.0, "revenue_growth": 11, "ebit_margin": 11,
     "eps_growth": 55, "fcf_growth": 40, "ev_ebitda": 16, "ps": 3.2, "pe": 40, "peg": 1.0},
    {"ticker": "AVGO", "name": "Broadcom", "sector": "Semiconductors",
     "price": 165.0, "market_cap": 770.0, "revenue_growth": 44, "ebit_margin": 45,
     "eps_growth": 30, "fcf_growth": 35, "ev_ebitda": 30, "ps": 18, "pe": 38, "peg": 1.5},
    {"ticker": "CRM", "name": "Salesforce", "sector": "Software",
     "price": 330.0, "market_cap": 260.0, "revenue_growth": 11, "ebit_margin": 20,
     "eps_growth": 40, "fcf_growth": 30, "ev_ebitda": 22, "ps": 7, "pe": 44, "peg": 1.2},
    {"ticker": "NOW", "name": "ServiceNow", "sector": "Software",
     "price": 900.0, "market_cap": 185.0, "revenue_growth": 23, "ebit_margin": 30,
     "eps_growth": 25, "fcf_growth": 28, "ev_ebitda": 55, "ps": 18, "pe": 90, "peg": 2.4},
    {"ticker": "PANW", "name": "Palo Alto Networks", "sector": "Software",
     "price": 340.0, "market_cap": 120.0, "revenue_growth": 20, "ebit_margin": 22,
     "eps_growth": 28, "fcf_growth": 26, "ev_ebitda": 45, "ps": 14, "pe": 55, "peg": 1.8},
    {"ticker": "LLY", "name": "Eli Lilly", "sector": "Pharma",
     "price": 890.0, "market_cap": 845.0, "revenue_growth": 36, "ebit_margin": 40,
     "eps_growth": 60, "fcf_growth": 30, "ev_ebitda": 40, "ps": 18, "pe": 70, "peg": 1.2},
    {"ticker": "COST", "name": "Costco", "sector": "Retail",
     "price": 900.0, "market_cap": 400.0, "revenue_growth": 6, "ebit_margin": 4,
     "eps_growth": 12, "fcf_growth": 10, "ev_ebitda": 25, "ps": 1.6, "pe": 55, "peg": 4.0},
    {"ticker": "V", "name": "Visa", "sector": "Financials",
     "price": 290.0, "market_cap": 560.0, "revenue_growth": 10, "ebit_margin": 67,
     "eps_growth": 14, "fcf_growth": 12, "ev_ebitda": 23, "ps": 16, "pe": 30, "peg": 2.0},
    {"ticker": "ADBE", "name": "Adobe", "sector": "Software",
     "price": 500.0, "market_cap": 225.0, "revenue_growth": 11, "ebit_margin": 35,
     "eps_growth": 15, "fcf_growth": 14, "ev_ebitda": 22, "ps": 9.5, "pe": 33, "peg": 1.7},
    {"ticker": "INTC", "name": "Intel", "sector": "Semiconductors",
     "price": 22.0, "market_cap": 90.0, "revenue_growth": -1, "ebit_margin": 4,
     "eps_growth": -30, "fcf_growth": -20, "ev_ebitda": 12, "ps": 2.5, "pe": 90, "peg": None},
    {"ticker": "F", "name": "Ford Motor", "sector": "Autos",
     "price": 11.0, "market_cap": 48.0, "revenue_growth": 5, "ebit_margin": 3,
     "eps_growth": 8, "fcf_growth": 6, "ev_ebitda": 9, "ps": 0.3, "pe": 12, "peg": 1.5},
    {"ticker": "SPOT", "name": "Spotify", "sector": "Media",
     "price": 470.0, "market_cap": 95.0, "revenue_growth": 16, "ebit_margin": 5,
     "eps_growth": 200, "fcf_growth": 80, "ev_ebitda": 25, "ps": 3.5, "pe": 60, "peg": 0.9},
    {"ticker": "WDAY", "name": "Workday", "sector": "Software",
     "price": 240.0, "market_cap": 63.0, "revenue_growth": 17, "ebit_margin": 24,
     "eps_growth": 22, "fcf_growth": 20, "ev_ebitda": 30, "ps": 7.5, "pe": 40, "peg": 1.6},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "sector": "Semiconductors",
     "price": 155.0, "market_cap": 250.0, "revenue_growth": 18, "ebit_margin": 22,
     "eps_growth": 35, "fcf_growth": 40, "ev_ebitda": 40, "ps": 11, "pe": 45, "peg": 1.3},
    {"ticker": "CDNS", "name": "Cadence Design", "sector": "Software",
     "price": 300.0, "market_cap": 82.0, "revenue_growth": 15, "ebit_margin": 30,
     "eps_growth": 18, "fcf_growth": 20, "ev_ebitda": 45, "ps": 18, "pe": 65, "peg": 1.9},
]


def seed_universe() -> list[dict]:
    """Return a copy of the curated seed universe."""
    return [dict(row) for row in _SEED]


def get_screener_universe() -> list[dict]:
    """Return the universe to screen.

    Demo mode → seed. Live mode → the SEC-built universe if available, else seed
    as a graceful fallback (the live pipeline is added in a later step).
    """
    if SETTINGS.is_demo:
        return seed_universe()
    try:
        from screener.universe_builder import build_live_universe

        live = build_live_universe()
        return live or seed_universe()
    except Exception:  # noqa: BLE001 — fall back so the page always works
        return seed_universe()
