"""Normalize SEC Company Facts (XBRL) into standardized FinancialFacts (§5, §10).

For each standardized metric we try its candidate XBRL tags in priority order and
take the first one present. Each fact records the exact tag and label it came
from, the accession, and a source URL. Confidence is HIGH for a company's use of
the primary standard tag, MEDIUM for an accepted alternate tag.

Duration facts are classified by period length: ~1 year → annual (FY), ~1 quarter
→ standalone quarter. Instant facts (balance sheet) are kept at their reporting
period. Cumulative YTD durations are left to quarterly_periods.py.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Optional

from config.metric_mappings import METRICS, MetricMap, Statement
from models.common import (
    Confidence,
    DataStatus,
    FiscalPeriod,
    Provenance,
)
from models.financial_fact import FinancialFact


def _parse_date(s: Optional[str]) -> Optional[_dt.date]:
    if not s:
        return None
    try:
        return _dt.date.fromisoformat(s)
    except ValueError:
        return None


def _unit_key_for(metric: MetricMap, units: dict[str, Any]) -> Optional[str]:
    """Pick the XBRL unit series that matches the metric's nature."""
    if metric.statement is Statement.SHARES:
        for k in ("shares",):
            if k in units:
                return k
    if metric.key in ("eps_basic", "eps_diluted"):
        for k in ("USD/shares",):
            if k in units:
                return k
    # Money metrics: prefer USD, else the first available unit.
    if "USD" in units:
        return "USD"
    return next(iter(units), None)


def _classify_duration(start: _dt.date, end: _dt.date) -> str:
    days = (end - start).days
    if 330 <= days <= 400:
        return "annual"
    if 80 <= days <= 100:
        return "quarter"
    return "other"  # H1 / 9-month cumulative — handled elsewhere


def _fiscal_period(fp_raw: Optional[str], kind: str) -> Optional[FiscalPeriod]:
    if kind == "annual":
        return FiscalPeriod.FY
    if fp_raw in ("Q1", "Q2", "Q3", "Q4"):
        return FiscalPeriod(fp_raw)
    return None


def normalize_company_facts(facts_json: dict) -> list[FinancialFact]:
    """Return a de-duplicated list of standardized annual/quarterly facts."""
    gaap = facts_json.get("facts", {}).get("us-gaap", {})
    cik = str(facts_json.get("cik", "")).zfill(10)
    base_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"

    # De-dupe by (metric, year, period, seg/geo, period_end); keep latest filed.
    chosen: dict[tuple, tuple[str, FinancialFact]] = {}

    for metric in METRICS:
        tag, priority = _first_present_tag(metric, gaap)
        if tag is None:
            continue
        concept = gaap[tag]
        label = concept.get("label") or tag
        units = concept.get("units", {})
        unit_key = _unit_key_for(metric, units)
        if unit_key is None:
            continue

        confidence = Confidence.HIGH if priority == 0 else Confidence.MEDIUM

        for entry in units[unit_key]:
            fact = _entry_to_fact(
                metric, tag, label, unit_key, entry, confidence, base_url
            )
            if fact is None:
                continue
            key = fact.key() + (fact.period_end or "",)
            filed = entry.get("filed", "")
            if key not in chosen or filed > chosen[key][0]:
                chosen[key] = (filed, fact)

    return [f for _, f in chosen.values()]


def _first_present_tag(
    metric: MetricMap, gaap: dict
) -> tuple[Optional[str], int]:
    for i, tag in enumerate(metric.tags):
        if tag in gaap:
            return tag, i
    return None, -1


def _entry_to_fact(
    metric: MetricMap,
    tag: str,
    label: str,
    unit_key: str,
    entry: dict,
    confidence: Confidence,
    base_url: str,
) -> Optional[FinancialFact]:
    val = entry.get("val")
    if val is None:
        return None
    fy = entry.get("fy")
    fp_raw = entry.get("fp")
    end = _parse_date(entry.get("end"))
    start = _parse_date(entry.get("start"))
    if end is None or fy is None:
        return None

    is_instant = start is None
    if is_instant:
        # Balance-sheet item: keep FY snapshots and quarter-end snapshots.
        period = FiscalPeriod.FY if fp_raw == "FY" else _fiscal_period(fp_raw, "quarter")
    else:
        kind = _classify_duration(start, end)
        if kind == "other":
            return None  # cumulative YTD; derived in quarterly_periods.py
        period = _fiscal_period(fp_raw, kind)
    if period is None:
        return None

    accession = entry.get("accn")
    src = f"{base_url}#{accession}" if accession else base_url
    return FinancialFact(
        metric=metric.key,
        value=float(val),
        fiscal_year=int(fy),
        fiscal_period=period,
        reported_label=label,
        unit=unit_key,
        currency="USD" if unit_key.startswith("USD") else unit_key,
        period_start=start.isoformat() if start else None,
        period_end=end.isoformat(),
        status=DataStatus.REPORTED,
        confidence=confidence,
        provenance=Provenance(
            source="SEC EDGAR",
            source_url=src,
            xbrl_tag=tag,
            filing_accession=accession,
            collected_at=_dt.date.today().isoformat(),
        ),
    )
