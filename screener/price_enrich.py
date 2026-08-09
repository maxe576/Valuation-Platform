"""Enrich the SEC fundamental universe with prices → valuation multiples.

SEC provides fundamentals but no prices, so the price-based screener metrics
(market cap, P/S, P/E, PEG) need a price feed. Reliable *keyless* bulk prices
aren't available, so this uses FMP's batch-quote endpoint when a free FMP key is
configured. Without a key it is a graceful no-op — the screener still runs on
fundamentals, and those criteria simply stay "n/a".
"""
from __future__ import annotations

from typing import Optional

from config.logging import get_logger
from services.fmp_client import FMPClient

log = get_logger("price_enrich")


def enrich_with_prices(universe: list[dict], fmp: Optional[FMPClient] = None) -> list[dict]:
    """Fill market_cap / pe / ps / peg / price in place when FMP is available."""
    fmp = fmp or FMPClient()
    if not fmp.enabled or not universe:
        return universe

    quotes = fmp.get_batch_quotes([d["ticker"] for d in universe])
    if not quotes:
        return universe

    filled = 0
    for d in universe:
        q = quotes.get(d["ticker"])
        if not q:
            continue
        price = q.get("price")
        mcap = q.get("marketCap")     # in USD
        pe = q.get("pe")
        rev = d.get("_revenue")
        d["price"] = price
        if mcap:
            d["market_cap"] = round(mcap / 1e9, 2)   # $B
            if rev:
                d["ps"] = round(mcap / rev, 2)
        if pe and pe > 0:
            d["pe"] = round(pe, 1)
            g = d.get("eps_growth")
            if g and g > 0:
                d["peg"] = round(pe / g, 2)          # PEG = P/E ÷ growth%
        filled += 1

    log.info("Enriched %d/%d names with FMP prices.", filled, len(universe))
    return universe
