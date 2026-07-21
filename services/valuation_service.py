"""Valuation orchestration (§14–22).

Runs every applicable method for a company and blends them into a fair-value
range. Engines stay pure; this service wires their inputs/outputs together and
produces a persistable :class:`ValuationRun` plus a rich in-memory result for the
UI. Reverse DCF is computed for diagnostics but never blended.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional

from config.lifecycle_weights import Lifecycle, Method, default_weights
from models.common import Confidence, Scenario
from models.forecast import AssumptionSet
from models.valuation import MethodResult, ValuationRun
from processing.ttm import net_debt as _net_debt
from valuation.blend import BlendInput, BlendResult, blend
from valuation.comps import CompResult, run_comp
from valuation.dcf import DCFResult, TerminalMethod, run_scenarios
from valuation.justified_multiple import RegressionResult, run_justified_multiple
from valuation.residual_income import ResidualIncomeResult, run_residual_income
from valuation.reverse_dcf import (
    ReverseDCFResult,
    implied_exit_multiple,
    implied_revenue_growth,
    implied_terminal_margin,
)
from valuation.sotp import SegmentMethod, SegmentValuation, SOTPResult, run_sotp


@dataclass
class ValuationInputs:
    ticker: str
    lifecycle: Lifecycle
    current_price: float
    assumption_set: AssumptionSet
    target: dict                       # revenue/ebitda/ebit/net_income/...
    peers: list[dict] = field(default_factory=list)
    segments: list[dict] = field(default_factory=list)
    residual_income: Optional[dict] = None


@dataclass
class FullValuation:
    ticker: str
    current_price: float
    dcf: dict[Scenario, DCFResult]
    comps: dict[str, CompResult]
    justified: Optional[RegressionResult]
    sotp: Optional[SOTPResult]
    residual_income: Optional[ResidualIncomeResult]
    reverse_dcf: list[ReverseDCFResult]
    blend: BlendResult
    bear: float
    base: float
    bull: float
    blended_value: float

    @property
    def upside(self) -> Optional[float]:
        if not self.current_price:
            return None
        return self.blended_value / self.current_price - 1.0

    @property
    def margin_of_safety(self) -> Optional[float]:
        # Downside cushion to the bear case (negative == price already below bear).
        if not self.blended_value:
            return None
        return self.bear / self.blended_value - 1.0

    @property
    def confidence_score(self) -> float:
        """0–100: high when methods agree (low dispersion) and few warnings."""
        disp = self.blend.dispersion
        score = max(0.0, 1.0 - disp) * 100.0
        score -= 5.0 * len(self.blend.warnings)
        return round(max(0.0, min(100.0, score)), 1)


def run_full_valuation(inputs: ValuationInputs) -> FullValuation:
    aset = inputs.assumption_set
    price = inputs.current_price
    net_debt = _net_debt(aset.total_debt, aset.cash, aset.investments)
    shares = aset.shares_outstanding
    target = inputs.target

    dcf = run_scenarios(aset, current_price=price)

    comps = _run_comps(inputs, net_debt, shares)
    justified = _run_justified(inputs, net_debt, shares)
    sotp = _run_sotp(inputs, aset)
    ri = _run_ri(inputs)
    reverse = _run_reverse(inputs, net_debt)

    blend_result = _blend_methods(inputs, dcf, comps, justified, sotp, ri)

    return FullValuation(
        ticker=inputs.ticker,
        current_price=price,
        dcf=dcf,
        comps=comps,
        justified=justified,
        sotp=sotp,
        residual_income=ri,
        reverse_dcf=reverse,
        blend=blend_result,
        bear=dcf[Scenario.BEAR].per_share_value,
        base=dcf[Scenario.BASE].per_share_value,
        bull=dcf[Scenario.BULL].per_share_value,
        blended_value=blend_result.blended_value,
    )


def _run_comps(inputs, net_debt, shares) -> dict[str, CompResult]:
    out: dict[str, CompResult] = {}
    if not inputs.peers:
        return out
    for metric, fundamental_key in (("ev_ebitda", "ebitda"), ("ev_revenue", "revenue")):
        vals = [p.get(metric) for p in inputs.peers if p.get(metric) is not None]
        fundamental = inputs.target.get(fundamental_key)
        if not vals or fundamental is None:
            continue
        out[metric] = run_comp(
            metric=metric,
            peer_multiples=vals,
            target_fundamental=fundamental,
            net_debt=net_debt,
            shares_outstanding=shares,
            target_own_multiple=inputs.target.get("own_ev_ebitda")
            if metric == "ev_ebitda" else None,
        )
    return out


def _run_justified(inputs, net_debt, shares) -> Optional[RegressionResult]:
    peers = [
        {"multiple": p.get("ev_ebitda"),
         "revenue_growth": p.get("revenue_growth"),
         "ebit_margin": p.get("ebit_margin")}
        for p in inputs.peers
    ]
    if len(peers) < 3 or inputs.target.get("ebitda") is None:
        return None
    return run_justified_multiple(
        peers=peers,
        target_features={
            "revenue_growth": inputs.target.get("revenue_growth", 0.0),
            "ebit_margin": inputs.target.get("ebit_margin", 0.0),
        },
        features=["revenue_growth", "ebit_margin"],
    )


def _run_sotp(inputs, aset) -> Optional[SOTPResult]:
    if not inputs.segments:
        return None
    segs = [
        SegmentValuation(
            name=s["name"],
            method=SegmentMethod.MULTIPLE,
            fundamental=s["revenue"] * s.get("ebitda_margin", 0.0),
            multiple=s.get("ev_ebitda", 0.0),
        )
        for s in inputs.segments
    ]
    return run_sotp(
        segs,
        cash=aset.cash,
        investments=aset.investments,
        total_debt=aset.total_debt,
        minority_interest=aset.minority_interest,
        shares_outstanding=aset.shares_outstanding,
    )


def _run_ri(inputs) -> Optional[ResidualIncomeResult]:
    ri = inputs.residual_income
    if not ri:
        return None
    return run_residual_income(
        beginning_book_value=ri["beginning_book_value"],
        net_income_forecast=ri["net_income_forecast"],
        cost_of_equity=ri.get("cost_of_equity", 0.10),
        terminal_growth=ri.get("terminal_growth", 0.03),
        shares_outstanding=inputs.assumption_set.shares_outstanding,
        dividend_payout_ratio=ri.get("dividend_payout_ratio", 0.0),
    )


def _run_reverse(inputs, net_debt) -> list[ReverseDCFResult]:
    aset = inputs.assumption_set
    base = aset.scenarios.get(Scenario.BASE)
    if base is None:
        return []
    bridge = dict(
        cash=aset.cash, investments=aset.investments, total_debt=aset.total_debt,
        minority_interest=aset.minority_interest,
        shares_outstanding=aset.shares_outstanding,
    )
    common = dict(
        base_year_revenue=aset.base_year_revenue, template=base,
        wacc=aset.wacc, terminal_growth=aset.terminal_growth,
        bridge=bridge, market_price=inputs.current_price,
    )
    return [
        implied_revenue_growth(exit_multiple=aset.exit_multiple, **common),
        implied_terminal_margin(exit_multiple=aset.exit_multiple, **common),
        implied_exit_multiple(**common),
    ]


def _blend_methods(inputs, dcf, comps, justified, sotp, ri) -> BlendResult:
    weights = default_weights(inputs.lifecycle)
    per_share: dict[Method, float] = {}
    conf: dict[Method, Confidence] = {}

    per_share[Method.DCF] = dcf[Scenario.BASE].per_share_value
    conf[Method.DCF] = Confidence.HIGH

    if "ev_ebitda" in comps:
        per_share[Method.COMPARABLES] = comps["ev_ebitda"].per_share_at_median
        conf[Method.COMPARABLES] = Confidence.MEDIUM
    if justified is not None:
        # Apply the predicted EV/EBITDA to target EBITDA → per share.
        from valuation.comps import MultipleType, apply_multiple
        net_debt = _net_debt(inputs.assumption_set.total_debt,
                             inputs.assumption_set.cash,
                             inputs.assumption_set.investments)
        per_share[Method.JUSTIFIED_MULTIPLE] = apply_multiple(
            MultipleType.EV, justified.applied_multiple,
            inputs.target.get("ebitda", 0.0), net_debt,
            inputs.assumption_set.shares_outstanding,
        )
        conf[Method.JUSTIFIED_MULTIPLE] = (
            Confidence.LOW if justified.is_weak else Confidence.MEDIUM
        )
    if sotp is not None:
        per_share[Method.SOTP] = sotp.per_share_value
        conf[Method.SOTP] = Confidence.MEDIUM
    if ri is not None:
        per_share[Method.RESIDUAL_INCOME] = ri.per_share_value
        conf[Method.RESIDUAL_INCOME] = Confidence.MEDIUM

    blend_inputs = [
        BlendInput(
            method=m,
            per_share_value=per_share[m],
            template_weight=w,
            confidence=conf.get(m, Confidence.MEDIUM),
        )
        for m, w in weights.items()
        if w > 0 and m in per_share
    ]
    return blend(blend_inputs)


def to_valuation_run(
    fv: FullValuation, lifecycle: Lifecycle, created_by: str = "system"
) -> ValuationRun:
    """Convert a FullValuation into a persistable, append-only ValuationRun."""
    method_results = [
        MethodResult(
            method=c.method,
            per_share_value=c.per_share_value,
            raw_weight=c.template_weight,
            normalized_weight=c.normalized_weight,
            results={"weighted_value": c.weighted_value},
        )
        for c in fv.blend.contributions
    ]
    return ValuationRun(
        company_ticker=fv.ticker,
        valuation_date=_dt.date.today().isoformat(),
        current_price=fv.current_price,
        bear_value=fv.bear,
        base_value=fv.base,
        bull_value=fv.bull,
        blended_value=fv.blended_value,
        company_lifecycle=lifecycle.value,
        method_results=method_results,
        created_by=created_by,
        created_at=_dt.datetime.now().isoformat(timespec="seconds"),
        run_payload={
            "confidence_score": fv.confidence_score,
            "dispersion": fv.blend.dispersion,
            "warnings": fv.blend.warnings,
        },
    )


def build_demo_valuation_inputs() -> ValuationInputs:
    """Assemble ValuationInputs for the demo company from the fixture."""
    from services.demo_data import build_default_assumptions, load_demo_fixture

    raw = load_demo_fixture()
    aset = build_default_assumptions(raw)
    return ValuationInputs(
        ticker=raw["company"]["ticker"],
        lifecycle=Lifecycle(raw["company"]["lifecycle"]),
        current_price=float(raw["current_price"]),
        assumption_set=aset,
        target=raw["target_metrics"],
        peers=raw["peers"],
        segments=raw["segments"],
        residual_income=raw["residual_income"],
    )
