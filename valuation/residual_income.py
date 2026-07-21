"""Residual-income valuation (§19).

For banks, insurers, and companies where book value is economically meaningful:

    Residual income_t = Net income_t − (Beginning book value_t × cost of equity)
    Equity value = Current book value
                   + Σ PV(forecast residual income)
                   + PV(terminal residual income)

Book value rolls forward by retained earnings (NI × (1 − payout)). Warns when
book value is not meaningful (e.g. negative equity).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RIYear:
    year_index: int
    beginning_book_value: float
    net_income: float
    equity_charge: float
    residual_income: float
    discount_factor: float
    pv_residual_income: float
    ending_book_value: float


@dataclass
class ResidualIncomeResult:
    beginning_book_value: float
    years: list[RIYear]
    pv_forecast_ri: float
    terminal_ri: float
    pv_terminal_ri: float
    equity_value: float
    per_share_value: float
    cost_of_equity: float
    terminal_growth: float
    warnings: list[str] = field(default_factory=list)


def run_residual_income(
    beginning_book_value: float,
    net_income_forecast: list[float],
    cost_of_equity: float,
    terminal_growth: float,
    shares_outstanding: float,
    dividend_payout_ratio: float = 0.0,
) -> ResidualIncomeResult:
    if not net_income_forecast:
        raise ValueError("Residual income requires at least one forecast year.")

    warnings: list[str] = []
    if beginning_book_value <= 0:
        warnings.append(
            "Beginning book value is non-positive; residual income is not "
            "economically meaningful for this company."
        )
    if cost_of_equity <= terminal_growth:
        warnings.append(
            f"Cost of equity ({cost_of_equity:.1%}) ≤ terminal growth "
            f"({terminal_growth:.1%}); terminal residual income is not meaningful."
        )

    years: list[RIYear] = []
    bv = beginning_book_value
    for t, ni in enumerate(net_income_forecast, start=1):
        equity_charge = bv * cost_of_equity
        ri = ni - equity_charge
        df = 1.0 / ((1.0 + cost_of_equity) ** t)
        ending_bv = bv + ni * (1.0 - dividend_payout_ratio)
        years.append(
            RIYear(
                year_index=t,
                beginning_book_value=bv,
                net_income=ni,
                equity_charge=equity_charge,
                residual_income=ri,
                discount_factor=df,
                pv_residual_income=ri * df,
                ending_book_value=ending_bv,
            )
        )
        bv = ending_bv

    pv_forecast = sum(y.pv_residual_income for y in years)

    last = years[-1]
    if cost_of_equity > terminal_growth:
        terminal_ri = last.residual_income * (1.0 + terminal_growth) / (
            cost_of_equity - terminal_growth
        )
    else:
        terminal_ri = 0.0
    pv_terminal = terminal_ri * last.discount_factor

    equity_value = beginning_book_value + pv_forecast + pv_terminal
    per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0.0
    if shares_outstanding <= 0:
        warnings.append("Share count is zero or negative; per-share value is invalid.")

    return ResidualIncomeResult(
        beginning_book_value=beginning_book_value,
        years=years,
        pv_forecast_ri=pv_forecast,
        terminal_ri=terminal_ri,
        pv_terminal_ri=pv_terminal,
        equity_value=equity_value,
        per_share_value=per_share,
        cost_of_equity=cost_of_equity,
        terminal_growth=terminal_growth,
        warnings=warnings,
    )
