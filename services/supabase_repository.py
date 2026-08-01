"""Supabase (PostgreSQL) Repository — cloud persistence (§8, §25).

Maps domain objects onto the §25 relational schema. Requires SUPABASE_URL +
SUPABASE_ANON_KEY and the migrations in database/ applied. The supabase client
is imported lazily so the app runs without the dependency; enable this backend by
configuring keys (the service-role key must never reach client code).

Valuation runs and assumption sets are append-only (no update/delete), preserving
the historical record.
"""
from __future__ import annotations

from typing import Optional

from config.logging import get_logger
from config.settings import SETTINGS
from models.ai_analysis import AIAnalysis
from models.common import Confidence, DataStatus, FiscalPeriod, Provenance
from models.company import Company
from models.filing import Filing
from models.financial_fact import FinancialFact
from models.forecast import AssumptionSet
from models.valuation import ValuationRun
from services import serialization as ser
from services.repository import Repository

log = get_logger("supabase_repository")


def _client():
    from supabase import create_client  # lazy: optional dependency

    return create_client(SETTINGS.supabase_url, SETTINGS.supabase_anon_key)


class SupabaseRepository(Repository):
    def __init__(self, client=None) -> None:
        if not SETTINGS.supabase_enabled and client is None:
            raise RuntimeError(
                "Supabase is not configured. Set SUPABASE_URL and "
                "SUPABASE_ANON_KEY, or use the SQLite/in-memory repository."
            )
        self.client = client or _client()

    # --- helpers ---
    def _company_id(self, ticker: str) -> Optional[int]:
        res = (self.client.table("companies").select("id")
               .eq("ticker", ticker.upper()).limit(1).execute())
        return res.data[0]["id"] if res.data else None

    # --- companies ---
    def save_company(self, company: Company) -> Company:
        payload = {
            "ticker": company.ticker, "name": company.name, "cik": company.cik,
            "sector": company.sector, "industry": company.industry,
            "fiscal_year_end": company.fiscal_year_end, "currency": company.currency,
            "lifecycle": company.lifecycle.value,
        }
        # Insert-if-new (avoids upsert, which would need UPDATE permission the
        # append-only policies don't grant). Companies rarely change; a refresh
        # of an existing company is a no-op here.
        existing = self._company_id(company.ticker)
        if existing is not None:
            company.id = existing
            return company
        res = self.client.table("companies").insert(payload).execute()
        if res.data:
            company.id = res.data[0]["id"]
        return company

    def get_company(self, ticker: str) -> Optional[Company]:
        res = (self.client.table("companies").select("*")
               .eq("ticker", ticker.upper()).limit(1).execute())
        if not res.data:
            return None
        return ser.company_from_dict(res.data[0])

    def list_companies(self) -> list[Company]:
        res = self.client.table("companies").select("*").execute()
        return [ser.company_from_dict(r) for r in res.data]

    # --- filings ---
    def save_filings(self, ticker: str, filings: list[Filing]) -> None:
        cid = self._company_id(ticker)
        if cid is None:
            return
        # Insert only accession numbers we don't already have (no upsert).
        existing = (self.client.table("filings").select("accession_number")
                    .eq("company_id", cid).execute())
        have = {r["accession_number"] for r in (existing.data or [])}
        rows = [{
            "company_id": cid, "accession_number": f.accession_number,
            "form_type": f.form_type.value, "filing_date": f.filing_date or None,
            "report_date": f.report_date, "primary_document": f.primary_document,
            "source_url": f.source_url, "processing_status": f.processing_status,
        } for f in filings if f.accession_number not in have]
        if rows:
            self.client.table("filings").insert(rows).execute()

    def get_filings(self, ticker: str) -> list[Filing]:
        cid = self._company_id(ticker)
        if cid is None:
            return []
        res = self.client.table("filings").select("*").eq("company_id", cid).execute()
        return [ser.filing_from_dict(r) for r in res.data]

    # --- facts ---
    def save_facts(self, ticker: str, facts: list[FinancialFact]) -> None:
        cid = self._company_id(ticker)
        if cid is None:
            return
        # Skip if this company's facts are already stored (avoid duplicates).
        existing = (self.client.table("financial_facts").select("id")
                    .eq("company_id", cid).limit(1).execute())
        if existing.data:
            return
        rows = [{
            "company_id": cid, "metric": f.metric, "reported_label": f.reported_label,
            "value": f.value, "unit": f.unit, "currency": f.currency,
            "period_start": f.period_start, "period_end": f.period_end,
            "fiscal_year": f.fiscal_year, "fiscal_period": f.fiscal_period.value,
            "segment": f.segment, "geography": f.geography,
            "xbrl_tag": f.provenance.xbrl_tag,
            "xbrl_dimensions": f.provenance.xbrl_dimensions,
            "data_status": f.status.value, "confidence": f.confidence.value,
            "source_url": f.provenance.source_url,
        } for f in facts]
        if rows:
            self.client.table("financial_facts").insert(rows).execute()

    def get_facts(self, ticker: str) -> list[FinancialFact]:
        cid = self._company_id(ticker)
        if cid is None:
            return []
        res = self.client.table("financial_facts").select("*").eq("company_id", cid).execute()
        out = []
        for r in res.data:
            out.append(FinancialFact(
                metric=r["metric"], value=r["value"], fiscal_year=r["fiscal_year"],
                fiscal_period=FiscalPeriod(r.get("fiscal_period", "FY")),
                reported_label=r.get("reported_label"), unit=r.get("unit", "USD"),
                currency=r.get("currency", "USD"), period_start=r.get("period_start"),
                period_end=r.get("period_end"), segment=r.get("segment"),
                geography=r.get("geography"),
                status=DataStatus(r.get("data_status", "reported")),
                confidence=Confidence(r.get("confidence", "high")),
                provenance=Provenance(source="SEC EDGAR", source_url=r.get("source_url"),
                                      xbrl_tag=r.get("xbrl_tag"),
                                      xbrl_dimensions=r.get("xbrl_dimensions")),
            ))
        return out

    # --- assumptions (append-only) ---
    def save_assumption_set(self, aset: AssumptionSet) -> AssumptionSet:
        cid = self._company_id(aset.company_ticker)
        payload = {
            "company_id": cid, "name": aset.name, "scenario": "combined",
            "model_version": aset.model_version,
            "assumptions": ser.to_jsonable(aset), "created_by": aset.created_by,
            "approved_by": aset.approved_by, "approval_status": aset.approval_status,
        }
        res = self.client.table("assumption_sets").insert(payload).execute()
        if res.data:
            aset.id = res.data[0]["id"]
        return aset

    def list_assumption_sets(self, ticker: str) -> list[AssumptionSet]:
        cid = self._company_id(ticker)
        if cid is None:
            return []
        res = (self.client.table("assumption_sets").select("*")
               .eq("company_id", cid).order("id").execute())
        return [ser.assumption_set_from_dict(r["assumptions"]) for r in res.data]

    # --- valuation runs (append-only) ---
    def save_valuation_run(self, run: ValuationRun) -> ValuationRun:
        cid = self._company_id(run.company_ticker)
        payload = {
            "company_id": cid, "ticker": run.company_ticker,
            "valuation_date": run.valuation_date, "current_price": run.current_price,
            "company_lifecycle": run.company_lifecycle,
            "bear_value": run.bear_value, "base_value": run.base_value,
            "bull_value": run.bull_value, "blended_value": run.blended_value,
            "confidence": run.confidence.value, "model_version": run.model_version,
            "created_by": run.created_by, "approval_status": run.approval_status,
            "run_payload": ser.to_jsonable(run),
        }
        res = self.client.table("valuation_runs").insert(payload).execute()
        if res.data:
            run.id = res.data[0]["id"]
            self._save_method_results(run)
        return run

    def _save_method_results(self, run: ValuationRun) -> None:
        rows = [{
            "valuation_run_id": run.id, "method": m.method.value,
            "equity_value": m.equity_value, "per_share_value": m.per_share_value,
            "raw_weight": m.raw_weight, "confidence": m.confidence.value,
            "normalized_weight": m.normalized_weight,
            "assumptions": m.assumptions, "results": m.results,
        } for m in run.method_results]
        if rows:
            self.client.table("method_results").insert(rows).execute()

    def list_valuation_runs(self, ticker: str) -> list[ValuationRun]:
        cid = self._company_id(ticker)
        if cid is None:
            return []
        res = (self.client.table("valuation_runs").select("run_payload")
               .eq("company_id", cid).order("id").execute())
        return [ser.valuation_run_from_dict(r["run_payload"]) for r in res.data]

    # --- ai analyses ---
    def save_ai_analysis(self, analysis: AIAnalysis) -> AIAnalysis:
        cid = self._company_id(analysis.company_ticker)
        payload = {
            "company_id": cid, "valuation_run_id": analysis.valuation_run_id,
            "analysis_type": analysis.analysis_type, "provider": analysis.provider,
            "model": analysis.model, "prompt_version": analysis.prompt_version,
            "input_sources": analysis.input_sources, "output": analysis.output,
            "analyst_approved": analysis.analyst_approved,
        }
        res = self.client.table("ai_analyses").insert(payload).execute()
        if res.data:
            analysis.id = res.data[0]["id"]
        return analysis

    def list_ai_analyses(self, ticker: str) -> list[AIAnalysis]:
        cid = self._company_id(ticker)
        if cid is None:
            return []
        res = (self.client.table("ai_analyses").select("*")
               .eq("company_id", cid).order("id").execute())
        out = []
        for r in res.data:
            out.append(AIAnalysis(
                company_ticker=ticker, analysis_type=r.get("analysis_type", ""),
                provider=r.get("provider", ""), model=r.get("model", ""),
                prompt_version=r.get("prompt_version", ""),
                input_sources=r.get("input_sources", []), output=r.get("output", {}),
                analyst_approved=r.get("analyst_approved", False),
                valuation_run_id=r.get("valuation_run_id"), id=r.get("id"),
            ))
        return out
