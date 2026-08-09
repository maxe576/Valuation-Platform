"""Auto-WACC builder (ported concept from the legacy Excel WACC sheet).

Computes the weighted-average cost of capital via CAPM, the same shape as the
Excel model:

    Cost of equity      = risk-free + beta × equity-risk-premium
    After-tax cost debt = pre-tax cost of debt × (1 − tax rate)
    WACC                = We × cost of equity + Wd × after-tax cost of debt

Inputs come from free sources where possible (risk-free from FRED, tax rate from
the company's filings) with transparent defaults; every input is overridable by
the analyst. Pure and unit-tested.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Transparent defaults (documented so analysts can challenge them).
DEFAULT_RISK_FREE = 0.043       # 10-year Treasury
DEFAULT_ERP = 0.050             # equity risk premium (~Damodaran)
DEFAULT_BETA = 1.0
DEFAULT_CREDIT_SPREAD = 0.015   # over risk-free, for cost of debt
DEFAULT_TAX_RATE = 0.21


@dataclass
class WACCResult:
    risk_free: float
    beta: float
    erp: float
    cost_of_equity: float
    pretax_cost_of_debt: float
    tax_rate: float
    after_tax_cost_of_debt: float
    equity_weight: float
    debt_weight: float
    wacc: float

    def breakdown(self) -> list[tuple[str, str]]:
        pct = lambda x: f"{x*100:.2f}%"
        return [
            ("Risk-free (10Y)", pct(self.risk_free)),
            ("Beta", f"{self.beta:.2f}"),
            ("Equity risk premium", pct(self.erp)),
            ("Cost of equity", pct(self.cost_of_equity)),
            ("Pre-tax cost of debt", pct(self.pretax_cost_of_debt)),
            ("Tax rate", pct(self.tax_rate)),
            ("After-tax cost of debt", pct(self.after_tax_cost_of_debt)),
            ("Equity / debt weight",
             f"{self.equity_weight*100:.0f} / {self.debt_weight*100:.0f}"),
            ("WACC", pct(self.wacc)),
        ]


def compute_wacc(
    risk_free: float = DEFAULT_RISK_FREE,
    beta: float = DEFAULT_BETA,
    erp: float = DEFAULT_ERP,
    pretax_cost_of_debt: Optional[float] = None,
    tax_rate: float = DEFAULT_TAX_RATE,
    equity_value: float = 1.0,
    debt_value: float = 0.0,
) -> WACCResult:
    """Compute WACC from CAPM. Weights derive from equity/debt values."""
    if pretax_cost_of_debt is None:
        pretax_cost_of_debt = risk_free + DEFAULT_CREDIT_SPREAD

    cost_of_equity = risk_free + beta * erp
    after_tax_kd = pretax_cost_of_debt * (1.0 - tax_rate)

    total = equity_value + debt_value
    we = (equity_value / total) if total > 0 else 1.0
    wd = 1.0 - we

    wacc = we * cost_of_equity + wd * after_tax_kd
    return WACCResult(
        risk_free=risk_free, beta=beta, erp=erp, cost_of_equity=cost_of_equity,
        pretax_cost_of_debt=pretax_cost_of_debt, tax_rate=tax_rate,
        after_tax_cost_of_debt=after_tax_kd, equity_weight=we, debt_weight=wd,
        wacc=wacc,
    )


def build_wacc_for_company(
    equity_value: float,
    debt_value: float,
    tax_rate: Optional[float] = None,
    beta: Optional[float] = None,
    risk_free: Optional[float] = None,
    erp: float = DEFAULT_ERP,
) -> WACCResult:
    """Convenience builder: pulls the risk-free from FRED (with fallback) and
    fills sensible defaults for anything not supplied."""
    if risk_free is None:
        try:
            from services.fred_client import FREDClient

            risk_free = FREDClient().risk_free_rate()
        except Exception:  # noqa: BLE001
            risk_free = DEFAULT_RISK_FREE
    return compute_wacc(
        risk_free=risk_free,
        beta=beta if beta is not None else DEFAULT_BETA,
        erp=erp,
        tax_rate=tax_rate if tax_rate is not None else DEFAULT_TAX_RATE,
        equity_value=equity_value,
        debt_value=debt_value,
    )
