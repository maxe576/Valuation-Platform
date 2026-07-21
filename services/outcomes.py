"""Outcome tracking & model-accuracy analytics (§9).

After a valuation, record the observed price at 3/6/12 months to measure realized
return and forecast error, then aggregate accuracy across saved runs — the basis
for evaluating which assumptions and methods were most reliable.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional

from models.valuation import ValuationOutcome, ValuationRun


def record_outcome(
    run: ValuationRun,
    horizon: str,
    observed_price: float,
    observed_date: Optional[str] = None,
) -> ValuationOutcome:
    """Compute realized return and forecast error for a saved run."""
    total_return = (observed_price / run.current_price - 1.0) if run.current_price else 0.0
    forecast_error = (
        (run.blended_value - observed_price) / observed_price
        if (run.blended_value is not None and observed_price) else 0.0
    )
    return ValuationOutcome(
        valuation_run_id=run.id,
        horizon=horizon,
        observed_date=observed_date or _dt.date.today().isoformat(),
        observed_price=observed_price,
        total_return=total_return,
        forecast_error=forecast_error,
    )


@dataclass
class AccuracySummary:
    n: int
    mean_abs_forecast_error: float
    direction_hit_rate: float        # share where predicted direction matched realized


def accuracy_summary(
    runs: list[ValuationRun], outcomes: list[ValuationOutcome]
) -> AccuracySummary:
    """Aggregate accuracy across runs given their outcomes.

    Direction hit = we predicted upside (blended > price) and price rose, or we
    predicted downside and price fell.
    """
    by_run = {r.id: r for r in runs}
    errs: list[float] = []
    hits = 0
    counted = 0
    for o in outcomes:
        run = by_run.get(o.valuation_run_id)
        if run is None or run.blended_value is None or not run.current_price:
            continue
        errs.append(abs(o.forecast_error))
        predicted_up = run.blended_value > run.current_price
        realized_up = o.total_return > 0
        if predicted_up == realized_up:
            hits += 1
        counted += 1

    mae = sum(errs) / len(errs) if errs else 0.0
    hit_rate = hits / counted if counted else 0.0
    return AccuracySummary(n=counted, mean_abs_forecast_error=mae,
                           direction_hit_rate=hit_rate)
