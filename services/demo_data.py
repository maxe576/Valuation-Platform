"""Demo-data mode (§2, §33): a populated repository with zero network calls.

Loads the bundled fixture company into an :class:`InMemoryRepository` and builds
a default bear/base/bull assumption set so every downstream feature — including
the DCF — is exercisable offline.
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from config.lifecycle_weights import Lifecycle
from config.settings import SETTINGS
from models.common import (
    Confidence,
    DataStatus,
    FiscalPeriod,
    Provenance,
    Scenario,
)
from models.company import Company
from models.financial_fact import FinancialFact
from models.forecast import AssumptionSet, ScenarioAssumptions
from services.repository import InMemoryRepository, Repository

DEMO_TICKER = "NFLX"


def _fixture_path() -> Path:
    return SETTINGS.demo_dir / "nflx.json"


def load_demo_fixture() -> dict:
    return json.loads(_fixture_path().read_text(encoding="utf-8"))


def _build_company(raw: dict) -> Company:
    c = raw["company"]
    return Company(
        ticker=c["ticker"],
        name=c["name"],
        cik=c.get("cik"),
        sector=c.get("sector"),
        industry=c.get("industry"),
        fiscal_year_end=c.get("fiscal_year_end"),
        currency=c.get("currency", "USD"),
        lifecycle=Lifecycle(c.get("lifecycle", "mature_profitable")),
    )


def _build_facts(raw: dict) -> list[FinancialFact]:
    prov = Provenance(source="DEMO fixture", collected_at=_dt.date.today().isoformat())
    facts: list[FinancialFact] = []
    for f in raw["facts"]:
        facts.append(
            FinancialFact(
                metric=f["metric"],
                value=float(f["value"]),
                fiscal_year=int(f["fiscal_year"]),
                fiscal_period=FiscalPeriod(f.get("fiscal_period", "FY")),
                reported_label=f.get("reported_label"),
                status=DataStatus.REPORTED,
                confidence=Confidence.HIGH,
                provenance=prov,
            )
        )
    return facts


def build_default_assumptions(raw: dict) -> AssumptionSet:
    """A reasonable 5-year bear/base/bull set for the demo company.

    Only revenue growth and EBIT margin differ across scenarios (mirrors the
    legacy Excel switch design); WACC, terminal growth, and the exit multiple are
    set at the assumption-set level.
    """
    base_rev = float(
        next(f["value"] for f in raw["facts"]
             if f["metric"] == "revenue" and f["fiscal_year"] == 2024)
    )
    bridge = raw["bridge"]

    def scen(scenario, growth, margin):
        n = len(growth)
        return ScenarioAssumptions(
            scenario=scenario,
            revenue_growth=growth,
            ebit_margin=margin,
            tax_rate=[0.14] * n,
            da_pct_sales=[0.38] * n,
            capex_pct_sales=[0.40, 0.38, 0.37, 0.36, 0.35][:n],
            nwc_pct_sales=[-0.005] * n,
        )

    scenarios = {
        Scenario.BEAR: scen(
            Scenario.BEAR,
            [0.09, 0.08, 0.07, 0.06, 0.05],
            [0.26, 0.26, 0.27, 0.27, 0.27],
        ),
        Scenario.BASE: scen(
            Scenario.BASE,
            [0.13, 0.12, 0.11, 0.10, 0.09],
            [0.28, 0.29, 0.30, 0.30, 0.31],
        ),
        Scenario.BULL: scen(
            Scenario.BULL,
            [0.16, 0.15, 0.14, 0.12, 0.11],
            [0.30, 0.32, 0.33, 0.34, 0.35],
        ),
    }

    return AssumptionSet(
        company_ticker=DEMO_TICKER,
        name="Demo base assumptions",
        base_year_revenue=base_rev,
        scenarios=scenarios,
        wacc=0.09,
        terminal_growth=0.03,
        exit_multiple=13.0,
        cash=float(bridge["cash"]),
        investments=float(bridge["investments"]),
        total_debt=float(bridge["total_debt"]),
        minority_interest=float(bridge["minority_interest"]),
        shares_outstanding=float(bridge["shares_outstanding"]),
        created_by="demo",
        approval_status="approved",
    )


def build_demo_repository() -> Repository:
    """Return an in-memory repository preloaded with the demo company."""
    raw = load_demo_fixture()
    repo = InMemoryRepository()
    repo.save_company(_build_company(raw))
    repo.save_facts(DEMO_TICKER, _build_facts(raw))
    repo.save_assumption_set(build_default_assumptions(raw))
    return repo


def demo_current_price() -> float:
    return float(load_demo_fixture()["current_price"])
