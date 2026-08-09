"""Build the live screener universe from SEC bulk data (free).

Assembles market-wide fundamentals from the SEC frames API and computes the
metrics the strategy scores on: revenue growth, EBIT margin, earnings growth (net
income growth as a proxy), and FCF growth. Price-based metrics (market cap,
multiples, PEG) require a price feed and are left as ``None`` for now — the
scoring engine excludes missing metrics rather than failing them.

The universe is filtered to a revenue floor to keep it to investable size, and
frame responses are cached on disk so rebuilds are fast.
"""
from __future__ import annotations

from typing import Optional

from config.logging import get_logger
from services.sec_frames import SECFramesClient

log = get_logger("universe_builder")

# Candidate latest complete fiscal years to probe (newest first).
_CANDIDATE_YEARS = [2025, 2024, 2023]

_REVENUE_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]
_MIN_REVENUE = 750_000_000.0   # $750M floor keeps the universe investable-sized


def _pct(cur: Optional[float], prev: Optional[float]) -> Optional[float]:
    """Year-over-year percent growth, only when the prior base is positive."""
    if cur is None or prev is None or prev <= 0:
        return None
    return round((cur / prev - 1.0) * 100.0, 1)


def _annual(client: SECFramesClient, tag_or_tags, year: int) -> dict[int, float]:
    period = f"CY{year}"
    if isinstance(tag_or_tags, list):
        return client.merged_frame(tag_or_tags, "USD", period)
    return client.frame(tag_or_tags, "USD", period)


def _find_latest_year(client: SECFramesClient) -> Optional[int]:
    for y in _CANDIDATE_YEARS:
        rev = client.merged_frame(_REVENUE_TAGS, "USD", f"CY{y}")
        if len(rev) > 100:  # a real, populated frame
            return y
    return None


def build_live_universe(
    client: Optional[SECFramesClient] = None,
    min_revenue: float = _MIN_REVENUE,
    max_names: int = 1500,
) -> list[dict]:
    """Return the live universe (list of metric dicts), or [] on failure."""
    client = client or SECFramesClient()
    year = _find_latest_year(client)
    if year is None:
        log.warning("No populated revenue frame found; live universe unavailable.")
        return []
    prev = year - 1

    rev_y = _annual(client, _REVENUE_TAGS, year)
    rev_p = _annual(client, _REVENUE_TAGS, prev)
    ebit_y = _annual(client, "OperatingIncomeLoss", year)
    ni_y = _annual(client, "NetIncomeLoss", year)
    ni_p = _annual(client, "NetIncomeLoss", prev)
    ocf_y = _annual(client, "NetCashProvidedByUsedInOperatingActivities", year)
    ocf_p = _annual(client, "NetCashProvidedByUsedInOperatingActivities", prev)
    capex_y = _annual(client, "PaymentsToAcquirePropertyPlantAndEquipment", year)
    capex_p = _annual(client, "PaymentsToAcquirePropertyPlantAndEquipment", prev)

    tickers = client.cik_to_ticker()

    universe: list[dict] = []
    for cik, r_now in rev_y.items():
        if r_now < min_revenue:
            continue
        info = tickers.get(cik)
        if not info or not info.get("ticker"):
            continue

        fcf_now = _fcf(ocf_y.get(cik), capex_y.get(cik))
        fcf_prev = _fcf(ocf_p.get(cik), capex_p.get(cik))
        ebit = ebit_y.get(cik)

        universe.append({
            "ticker": info["ticker"],
            "name": info["name"],
            "sector": None,
            "revenue_growth": _pct(r_now, rev_p.get(cik)),
            "ebit_margin": round(ebit / r_now * 100.0, 1) if (ebit is not None and r_now) else None,
            "eps_growth": _pct(ni_y.get(cik), ni_p.get(cik)),
            "fcf_growth": _pct(fcf_now, fcf_prev),
            # Price-based metrics pending a price feed:
            "market_cap": None, "ev_ebitda": None, "ps": None,
            "pe": None, "peg": None, "price": None,
            "_revenue": r_now, "_fiscal_year": year,
        })

    # Largest by revenue first; cap the size.
    universe.sort(key=lambda d: d.get("_revenue", 0), reverse=True)
    universe = universe[:max_names]
    log.info("Built live universe: %d names (FY%d, revenue ≥ $%.0fM)",
             len(universe), year, min_revenue / 1e6)
    return universe


def _fcf(ocf: Optional[float], capex: Optional[float]) -> Optional[float]:
    if ocf is None:
        return None
    return ocf - abs(capex) if capex is not None else ocf
