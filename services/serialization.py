"""JSON (de)serialization for domain models (§8 persistence).

Encoding is generic (dataclasses/enums/collections → JSON-safe). Decoding is
explicit per entity so nested dataclasses and enums round-trip exactly — used by
both the SQLite and Supabase repositories so a saved valuation reopens intact.
"""
from __future__ import annotations

import dataclasses
import enum
from typing import Any

from config.lifecycle_weights import Lifecycle, Method
from models.ai_analysis import AIAnalysis
from models.common import (
    Confidence,
    DataStatus,
    FilingType,
    FiscalPeriod,
    Provenance,
    Scenario,
)
from models.company import Company
from models.filing import Filing
from models.financial_fact import FinancialFact
from models.forecast import Assumption, AssumptionSet, ScenarioAssumptions
from models.valuation import MethodResult, ValuationRun


# --- generic encoder -------------------------------------------------------

def to_jsonable(o: Any) -> Any:
    if isinstance(o, enum.Enum):
        return o.value
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return {f.name: to_jsonable(getattr(o, f.name)) for f in dataclasses.fields(o)}
    if isinstance(o, dict):
        return {(k.value if isinstance(k, enum.Enum) else k): to_jsonable(v)
                for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(x) for x in o]
    return o


# --- explicit decoders -----------------------------------------------------

def company_from_dict(d: dict) -> Company:
    return Company(
        ticker=d["ticker"], name=d["name"], cik=d.get("cik"),
        sector=d.get("sector"), industry=d.get("industry"),
        fiscal_year_end=d.get("fiscal_year_end"), currency=d.get("currency", "USD"),
        lifecycle=Lifecycle(d.get("lifecycle", "mature_profitable")),
        id=d.get("id"),
    )


def _provenance_from_dict(d: dict | None) -> Provenance:
    if not d:
        return Provenance()
    return Provenance(
        source=d.get("source", ""), source_url=d.get("source_url"),
        xbrl_tag=d.get("xbrl_tag"), xbrl_dimensions=d.get("xbrl_dimensions"),
        filing_accession=d.get("filing_accession"), collected_at=d.get("collected_at"),
    )


def fact_from_dict(d: dict) -> FinancialFact:
    return FinancialFact(
        metric=d["metric"], value=d["value"], fiscal_year=d["fiscal_year"],
        fiscal_period=FiscalPeriod(d.get("fiscal_period", "FY")),
        reported_label=d.get("reported_label"), unit=d.get("unit", "USD"),
        currency=d.get("currency", "USD"), period_start=d.get("period_start"),
        period_end=d.get("period_end"), segment=d.get("segment"),
        geography=d.get("geography"),
        status=DataStatus(d.get("status", "reported")),
        confidence=Confidence(d.get("confidence", "high")),
        provenance=_provenance_from_dict(d.get("provenance")),
        analyst_override=d.get("analyst_override", False),
        override_reason=d.get("override_reason"),
    )


def filing_from_dict(d: dict) -> Filing:
    return Filing(
        accession_number=d["accession_number"],
        form_type=FilingType(d.get("form_type", "other")),
        filing_date=d.get("filing_date", ""), report_date=d.get("report_date"),
        primary_document=d.get("primary_document"), source_url=d.get("source_url"),
        processing_status=d.get("processing_status", "pending"),
        company_cik=d.get("company_cik"), id=d.get("id"),
    )


def _scenario_from_dict(d: dict) -> ScenarioAssumptions:
    rationales = {
        k: Assumption(**v) for k, v in (d.get("rationales") or {}).items()
    }
    return ScenarioAssumptions(
        scenario=Scenario(d["scenario"]),
        revenue_growth=d.get("revenue_growth", []),
        ebit_margin=d.get("ebit_margin", []),
        tax_rate=d.get("tax_rate", []),
        da_pct_sales=d.get("da_pct_sales", []),
        capex_pct_sales=d.get("capex_pct_sales", []),
        nwc_pct_sales=d.get("nwc_pct_sales", []),
        rationales=rationales,
    )


def assumption_set_from_dict(d: dict) -> AssumptionSet:
    scenarios = {
        Scenario(k): _scenario_from_dict(v) for k, v in d.get("scenarios", {}).items()
    }
    return AssumptionSet(
        company_ticker=d["company_ticker"], name=d["name"],
        base_year_revenue=d["base_year_revenue"], scenarios=scenarios,
        wacc=d.get("wacc", 0.10), terminal_growth=d.get("terminal_growth", 0.025),
        exit_multiple=d.get("exit_multiple", 12.0), cash=d.get("cash", 0.0),
        investments=d.get("investments", 0.0), total_debt=d.get("total_debt", 0.0),
        minority_interest=d.get("minority_interest", 0.0),
        shares_outstanding=d.get("shares_outstanding", 0.0),
        model_version=d.get("model_version", "dcf-1.0"),
        created_by=d.get("created_by"), approved_by=d.get("approved_by"),
        approval_status=d.get("approval_status", "draft"), id=d.get("id"),
    )


def _method_result_from_dict(d: dict) -> MethodResult:
    return MethodResult(
        method=Method(d["method"]), per_share_value=d["per_share_value"],
        equity_value=d.get("equity_value"), raw_weight=d.get("raw_weight", 0.0),
        confidence=Confidence(d.get("confidence", "medium")),
        normalized_weight=d.get("normalized_weight", 0.0),
        assumptions=d.get("assumptions", {}), results=d.get("results", {}),
        included_in_blend=d.get("included_in_blend", True),
    )


def valuation_run_from_dict(d: dict) -> ValuationRun:
    return ValuationRun(
        company_ticker=d["company_ticker"], valuation_date=d["valuation_date"],
        current_price=d["current_price"], bear_value=d.get("bear_value"),
        base_value=d.get("base_value"), bull_value=d.get("bull_value"),
        blended_value=d.get("blended_value"),
        confidence=Confidence(d.get("confidence", "medium")),
        company_lifecycle=d.get("company_lifecycle"),
        assumption_set_id=d.get("assumption_set_id"),
        model_version=d.get("model_version", "dcf-1.0"),
        created_by=d.get("created_by"), approval_status=d.get("approval_status", "draft"),
        method_results=[_method_result_from_dict(m) for m in d.get("method_results", [])],
        run_payload=d.get("run_payload", {}), created_at=d.get("created_at"),
        id=d.get("id"),
    )


def ai_analysis_from_dict(d: dict) -> AIAnalysis:
    return AIAnalysis(
        company_ticker=d["company_ticker"], analysis_type=d["analysis_type"],
        provider=d["provider"], model=d["model"], prompt_version=d["prompt_version"],
        input_sources=d.get("input_sources", []), output=d.get("output", {}),
        analyst_approved=d.get("analyst_approved", False),
        valuation_run_id=d.get("valuation_run_id"), created_at=d.get("created_at"),
        id=d.get("id"),
    )
