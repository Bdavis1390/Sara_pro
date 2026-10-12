from __future__ import annotations

import numpy as np

from .forward import coefficients
from .schema import InferenceResult, Measurement


def infer(measurements: list[Measurement], cond_limit: float = 1.0e4) -> InferenceResult:
    if len(measurements) < 4:
        raise ValueError("at least four measurements are required")

    rows = []
    target = []
    for m in measurements:
        baseline, c_am, c_relax = coefficients(m.ef, m.theta_rad, m.phi_rad)
        rows.append([c_am, c_relax])
        target.append(m.value - baseline)

    X = np.asarray(rows, dtype=float)
    y = np.asarray(target, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    amplitude = float(beta[0])
    inv_tau = float(beta[1])
    if inv_tau <= 0:
        raise ValueError("inferred inverse relaxation time is non-positive")
    tau = 1.0 / inv_tau

    residual = y - X @ beta
    sse = float(residual @ residual)
    dof = max(1, len(y) - X.shape[1])
    variance = sse / dof
    xtx_inv = np.linalg.pinv(X.T @ X)
    covariance_beta = variance * xtx_inv

    # Convert covariance from (A, 1/tau) to (A, tau) with a local Jacobian.
    jac = np.array([[1.0, 0.0], [0.0, -1.0 / (inv_tau * inv_tau)]])
    covariance = jac @ covariance_beta @ jac.T
    condition = float(np.linalg.cond(X))
    identifiable = bool(np.isfinite(condition) and condition < cond_limit)

    return InferenceResult(
        amplitude=amplitude,
        tau=tau,
        covariance=(
            (float(covariance[0, 0]), float(covariance[0, 1])),
            (float(covariance[1, 0]), float(covariance[1, 1])),
        ),
        condition_number=condition,
        identifiable=identifiable,
        sse=sse,
    )


def fit_relaxation_only(measurements: list[Measurement]) -> dict[str, float]:
    rows = []
    target = []
    for m in measurements:
        baseline, _, c_relax = coefficients(m.ef, m.theta_rad, m.phi_rad)
        rows.append([c_relax])
        target.append(m.value - baseline)

    X = np.asarray(rows, dtype=float)
    y = np.asarray(target, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    residual = y - X @ beta
    sse = float(residual @ residual)
    inv_tau = float(beta[0])
    tau = float("inf") if inv_tau <= 0 else 1.0 / inv_tau
    return {"tau": tau, "sse": sse}
