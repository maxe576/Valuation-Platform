"""Justified-multiple regression (§17).

Regress a valuation multiple on fundamental drivers across the peer set (OLS),
then predict the multiple the target *deserves* from its own fundamentals. The
model reports coefficients, R², observation count, and residuals, and flags weak
regressions (too few complete observations, or low explanatory power) so a thin
result is never presented as reliable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class RegressionResult:
    features: list[str]
    intercept: float
    coefficients: dict[str, float]
    r_squared: float
    n_observations: int
    residuals: list[float]
    predicted_target_multiple: float
    applied_multiple: float                 # after optional cap/override
    warnings: list[str] = field(default_factory=list)
    override_reason: Optional[str] = None

    @property
    def is_weak(self) -> bool:
        return bool(self.warnings)


def run_justified_multiple(
    peers: list[dict],
    target_features: dict[str, float],
    features: list[str],
    multiple_key: str = "multiple",
    cap: Optional[float] = None,
    override_multiple: Optional[float] = None,
    override_reason: Optional[str] = None,
    min_observations: int = 5,
    weak_r2: float = 0.30,
) -> RegressionResult:
    """Fit ``multiple ~ features`` over peers and predict the target multiple.

    ``peers`` is a list of dicts each containing ``multiple_key`` and every name
    in ``features``. Rows missing any required value are dropped.
    """
    if not features:
        raise ValueError("At least one explanatory feature is required.")

    rows = [
        p for p in peers
        if p.get(multiple_key) is not None
        and all(p.get(f) is not None for f in features)
    ]
    n = len(rows)

    warnings: list[str] = []
    # Need more observations than parameters (k features + intercept) with margin.
    if n < max(min_observations, len(features) + 2):
        warnings.append(
            f"Only {n} complete peer observations for {len(features)} feature(s); "
            "regression is under-identified and should not be relied upon."
        )

    y = np.array([float(r[multiple_key]) for r in rows])
    X = np.array([[1.0] + [float(r[f]) for f in features] for r in rows])

    if n == 0:
        raise ValueError("No complete peer observations for the regression.")

    # Least squares; guard singular designs.
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    preds = X @ beta
    resid = y - preds
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    if ss_tot > 0 and r2 < weak_r2 and not warnings:
        warnings.append(
            f"R² is low ({r2:.2f}); the chosen drivers explain little of the "
            "cross-peer multiple variation."
        )

    intercept = float(beta[0])
    coefs = {f: float(beta[i + 1]) for i, f in enumerate(features)}

    x_target = np.array([1.0] + [float(target_features[f]) for f in features])
    predicted = float(x_target @ beta)

    applied = predicted
    if cap is not None and applied > cap:
        applied = cap
    if override_multiple is not None:
        applied = override_multiple

    return RegressionResult(
        features=features,
        intercept=intercept,
        coefficients=coefs,
        r_squared=r2,
        n_observations=n,
        residuals=[float(r) for r in resid],
        predicted_target_multiple=predicted,
        applied_multiple=applied,
        warnings=warnings,
        override_reason=override_reason,
    )
