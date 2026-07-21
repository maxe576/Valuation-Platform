"""DCF sensitivity tables (§14).

Two-way grids of implied per-share value:
  * WACC × terminal growth  (perpetual-growth terminal)
  * WACC × exit multiple    (exit-multiple terminal)
  * revenue growth × EBIT margin (uniform additive shifts to the driver paths)

Each builder re-runs the DCF engine over the grid — no duplicated math.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from models.forecast import AssumptionSet, ScenarioAssumptions
from .dcf import TerminalMethod, run_dcf


@dataclass
class SensitivityTable:
    row_label: str
    col_label: str
    row_values: list[float]
    col_values: list[float]
    cells: list[list[float]]   # cells[r][c] = per-share value


def _per_share(
    aset: AssumptionSet,
    sa: ScenarioAssumptions,
    wacc: float,
    terminal_growth: float,
    exit_multiple: float,
    method: TerminalMethod,
) -> float:
    res = run_dcf(
        base_year_revenue=aset.base_year_revenue,
        scenario_assumptions=sa,
        wacc=wacc,
        terminal_growth=terminal_growth,
        exit_multiple=exit_multiple,
        cash=aset.cash,
        investments=aset.investments,
        total_debt=aset.total_debt,
        minority_interest=aset.minority_interest,
        shares_outstanding=aset.shares_outstanding,
        terminal_method=method,
    )
    return res.per_share_value


def wacc_vs_terminal_growth(
    aset: AssumptionSet,
    sa: ScenarioAssumptions,
    wacc_values: list[float],
    growth_values: list[float],
) -> SensitivityTable:
    cells = [
        [
            _per_share(aset, sa, w, g, aset.exit_multiple,
                       TerminalMethod.PERPETUAL_GROWTH)
            for g in growth_values
        ]
        for w in wacc_values
    ]
    return SensitivityTable("WACC", "Terminal growth", wacc_values, growth_values, cells)


def wacc_vs_exit_multiple(
    aset: AssumptionSet,
    sa: ScenarioAssumptions,
    wacc_values: list[float],
    multiple_values: list[float],
) -> SensitivityTable:
    cells = [
        [
            _per_share(aset, sa, w, aset.terminal_growth, m,
                       TerminalMethod.EXIT_MULTIPLE)
            for m in multiple_values
        ]
        for w in wacc_values
    ]
    return SensitivityTable("WACC", "Exit multiple", wacc_values, multiple_values, cells)


def growth_vs_margin(
    aset: AssumptionSet,
    sa: ScenarioAssumptions,
    growth_deltas: list[float],
    margin_deltas: list[float],
    method: TerminalMethod = TerminalMethod.PERPETUAL_GROWTH,
) -> SensitivityTable:
    """Apply uniform additive shifts to every forecast year's growth and margin."""
    cells: list[list[float]] = []
    for gd in growth_deltas:
        row: list[float] = []
        for md in margin_deltas:
            shifted = replace(
                sa,
                revenue_growth=[g + gd for g in sa.revenue_growth],
                ebit_margin=[m + md for m in sa.ebit_margin],
            )
            row.append(
                _per_share(aset, shifted, aset.wacc, aset.terminal_growth,
                           aset.exit_multiple, method)
            )
        cells.append(row)
    return SensitivityTable(
        "Δ revenue growth", "Δ EBIT margin", growth_deltas, margin_deltas, cells
    )
