"""SQLite persistence round-trip tests (§29 database save/retrieve)."""
from __future__ import annotations

from config.lifecycle_weights import Lifecycle
from models.common import Confidence, DataStatus, FiscalPeriod, Provenance
from models.company import Company
from models.financial_fact import FinancialFact
from services.serialization import to_jsonable
from services.sqlite_repository import SQLiteRepository
from services.valuation_service import (
    build_demo_valuation_inputs,
    run_full_valuation,
    to_valuation_run,
)


def _repo(tmp_path):
    return SQLiteRepository(db_path=str(tmp_path / "test.sqlite"))


def test_company_and_facts_round_trip(tmp_path):
    repo = _repo(tmp_path)
    repo.save_company(Company(ticker="NFLX", name="Netflix, Inc.",
                              lifecycle=Lifecycle.HIGH_GROWTH_PROFITABLE, cik="0001065280"))
    facts = [FinancialFact(
        metric="revenue", value=39_000_000_000, fiscal_year=2024,
        fiscal_period=FiscalPeriod.FY, status=DataStatus.REPORTED,
        confidence=Confidence.HIGH,
        provenance=Provenance(source="SEC EDGAR", xbrl_tag="Revenues"),
    )]
    repo.save_facts("NFLX", facts)

    # Reopen with a fresh connection to the same file.
    repo2 = SQLiteRepository(db_path=str(tmp_path / "test.sqlite"))
    c = repo2.get_company("NFLX")
    assert c is not None and c.name == "Netflix, Inc."
    assert c.lifecycle is Lifecycle.HIGH_GROWTH_PROFITABLE
    assert c.cik == "0001065280"
    got = repo2.get_facts("NFLX")
    assert len(got) == 1
    assert got[0].metric == "revenue" and got[0].value == 39_000_000_000
    assert got[0].confidence is Confidence.HIGH
    assert got[0].provenance.xbrl_tag == "Revenues"


def test_valuation_run_is_appended_and_reopens(tmp_path):
    repo = _repo(tmp_path)
    inputs = build_demo_valuation_inputs()
    fv = run_full_valuation(inputs)
    run = to_valuation_run(fv, inputs.lifecycle)

    repo.save_valuation_run(run)
    repo.save_valuation_run(run)  # append again — history is not overwritten

    repo2 = SQLiteRepository(db_path=str(tmp_path / "test.sqlite"))
    runs = repo2.list_valuation_runs("NFLX")
    assert len(runs) == 2
    assert runs[0].blended_value == round(fv.blended_value, 2) or runs[0].blended_value == fv.blended_value
    assert runs[0].method_results  # nested method results survive the round-trip


def test_assumption_set_round_trip(tmp_path):
    repo = _repo(tmp_path)
    inputs = build_demo_valuation_inputs()
    saved = repo.save_assumption_set(inputs.assumption_set)
    assert saved.id is not None

    repo2 = SQLiteRepository(db_path=str(tmp_path / "test.sqlite"))
    sets = repo2.list_assumption_sets("NFLX")
    assert len(sets) == 1
    from models.common import Scenario
    assert Scenario.BASE in sets[0].scenarios
    assert sets[0].wacc == inputs.assumption_set.wacc


def test_to_jsonable_handles_enums_and_dataclasses():
    inputs = build_demo_valuation_inputs()
    blob = to_jsonable(inputs.assumption_set)
    # Enum keys become their string values.
    assert "bear" in blob["scenarios"]
    assert isinstance(blob["wacc"], float)
