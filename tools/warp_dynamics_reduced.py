#!/usr/bin/env python3
"""
Worldshepherd Warp Dynamics reduced screening tool.

Purpose
-------
Adversarially screen reduced warp/analogue source models before any full-GR claim.

Claims boundary
---------------
- This is NOT a warp-drive simulator.
- Passing a reduced gate does NOT imply a valid Einstein-matter solution.
- Full-GR constraints, observer-robust energy conditions, and laboratory gravity
  remain separate unresolved gates.

Implemented screens
-------------------
1. Pressureless Alcubierre-like characteristic caustic benchmark.
2. Passive wall-width / caustic-time bound.
3. Global damping operational no-go.
4. 1-D special-relativistic hydrodynamics (SRHD), gamma-law EOS, HLL flux.
5. Resolution-based shock suspicion flag.
6. Perturbation ensemble support.
7. Machine-readable claims state / promotion decision.

Units: c = R = rho0 = 1 unless otherwise stated.
"""

from __future__ import annotations
import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


@dataclass
class Gates:
    density_ratio_max: float = 2.0
    peak_retention_min: float = 0.90
    sound_speed_max: float = 1.0
    shock_gradient_ratio_max: float = 1.50
    perturbation_pass_fraction_min: float = 0.95
    compact_wall_width_over_R_max: float = 0.50


@dataclass
class Result:
    gamma: float
    cs0: float
    sigma_R: float
    nx: int
    max_density_ratio: float
    peak_retention: float
    max_sound_speed: float
    max_abs_dv_dx: float
    min_density: float
    min_pressure: float


def shape_profile(x: np.ndarray, sigma_R: float, vs: float = 0.3, R: float = 1.0) -> np.ndarray:
    sigma = sigma_R / R
    return vs * (
        np.tanh(sigma * (x + R)) - np.tanh(sigma * (x - R))
    ) / (2.0 * np.tanh(sigma * R))


def caustic_time_pressureless(x: np.ndarray, u: np.ndarray) -> float:
    du = np.gradient(u, x)
    m = float(np.min(du))
    return math.inf if m >= 0.0 else -1.0 / m


def wall_width_10_90(sigma_R: float, R: float = 1.0) -> float:
    x = np.linspace(0.0, 6.0 * R, 30001)
    f = shape_profile(x, sigma_R=sigma_R, vs=1.0, R=R)
    def cross(level: float) -> float:
        idx = np.flatnonzero(f <= level)
        if not len(idx):
            return math.nan
        i = int(idx[0])
        if i == 0:
            return float(x[0])
        x0, x1 = x[i-1], x[i]
        y0, y1 = f[i-1], f[i]
        return float(x0 + (level-y0)*(x1-x0)/(y1-y0))
    return cross(0.1) - cross(0.9)


def passive_compactness_bound(width_over_R: float) -> float:
    # A 0.9->0.1 drop forces |du/dx| >= 0.8 v/W.
    # Thus t_c v/R <= (W/R)/0.8.
    return width_over_R / 0.8


def p_from_cs(rho: float, cs: float, gamma: float) -> float:
    a = gamma / (gamma - 1.0)
    den = gamma - a * cs * cs
    if den <= 0:
        raise ValueError("Requested initial sound speed incompatible with gamma-law EOS.")
    return rho * cs * cs / den


def prim_to_cons(rho: np.ndarray, v: np.ndarray, p: np.ndarray, gamma: float) -> np.ndarray:
    W = 1.0 / np.sqrt(1.0 - v*v)
    h = 1.0 + gamma/(gamma-1.0) * p/rho
    D = rho * W
    S = rho * h * W*W * v
    tau = rho * h * W*W - p - D
    return np.array([D, S, tau])


def cons_to_prim(U: np.ndarray, gamma: float, p_init: np.ndarray | None = None) -> Tuple[np.ndarray,...]:
    D, S, tau = U
    E = tau + D
    pmin = np.maximum(1e-12, np.abs(S) - E + 1e-10)
    if p_init is None:
        p = np.maximum((gamma-1.0)*np.maximum(tau, 1e-10), pmin*1.1)
    else:
        p = np.maximum(p_init, pmin*1.0001)

    a = gamma/(gamma-1.0)
    for _ in range(60):
        Q = np.maximum(E+p, np.abs(S)*(1.0+1e-12))
        v = np.clip(S/Q, -0.999999999, 0.999999999)
        W = 1.0/np.sqrt(1.0-v*v)
        f = D*W + a*p*W*W - Q
        dW = -(W**3)*(v*v)/Q
        df = D*dW + a*W*W + 2.0*a*p*W*dW - 1.0
        pnew = p - f/df
        bad = (pnew <= pmin) | ~np.isfinite(pnew)
        pnew[bad] = 0.5*(p[bad]+pmin[bad])
        if np.max(np.abs(pnew-p)/(p+1e-12)) < 1e-10:
            p = pnew
            break
        p = pnew

    Q = E+p
    v = np.clip(S/Q, -0.999999, 0.999999)
    W = 1.0/np.sqrt(1.0-v*v)
    rho = D/W
    h = 1.0 + a*p/rho
    cs2 = gamma*p/(rho*h)
    return rho, v, p, np.sqrt(np.maximum(cs2, 0.0))


def flux(U: np.ndarray, prim: Tuple[np.ndarray,...]) -> np.ndarray:
    D, S, tau = U
    rho, v, p, cs = prim
    return np.array([D*v, S*v+p, S-D*v])


def hll_flux(UL: np.ndarray, UR: np.ndarray, primL, primR) -> np.ndarray:
    FL, FR = flux(UL, primL), flux(UR, primR)
    _, vL, _, cL = primL
    _, vR, _, cR = primR
    lmL = (vL-cL)/(1.0-vL*cL)
    lpL = (vL+cL)/(1.0+vL*cL)
    lmR = (vR-cR)/(1.0-vR*cR)
    lpR = (vR+cR)/(1.0+vR*cR)
    sL = np.minimum(lmL, lmR)
    sR = np.maximum(lpL, lpR)
    FH = np.empty_like(FL)
    left = sL >= 0.0
    right = sR <= 0.0
    mid = ~(left | right)
    FH[:,left] = FL[:,left]
    FH[:,right] = FR[:,right]
    FH[:,mid] = (
        sR[mid]*FL[:,mid] - sL[mid]*FR[:,mid]
        + (sL[mid]*sR[mid])[None,:]*(UR[:,mid]-UL[:,mid])
    )/(sR[mid]-sL[mid])[None,:]
    return FH


def correlated_noise(x: np.ndarray, seed: int, modes: int = 6) -> np.ndarray:
    rng = np.random.default_rng(seed)
    coeff = rng.normal(size=modes)
    n = sum(
        coeff[k] * np.sin(2.0*np.pi*(k+1)*(x-x[0])/(x[-1]-x[0]))/(k+1)
        for k in range(modes)
    )
    n = (n-n.mean())/n.std()
    return n


def run_srhd(
    gamma: float,
    cs0: float,
    sigma_R: float = 8.0,
    nx: int = 600,
    vs: float = 0.3,
    horizon_baseline_tc: float = 5.0,
    perturbation: float = 0.0,
    seed: int = 1,
) -> Result:
    if gamma > 2.0:
        raise ValueError("gamma>2 rejected: gamma-law high-energy sound-speed limit is acausal.")
    xmin, xmax = -8.0, 12.0
    x = np.linspace(xmin, xmax, nx)
    dx = x[1]-x[0]
    rho = np.ones(nx)
    v = shape_profile(x, sigma_R=sigma_R, vs=vs)
    if perturbation:
        v *= 1.0 + perturbation*correlated_noise(x, seed)
        v = np.clip(v, -0.95, 0.95)

    p0 = p_from_cs(1.0, cs0, gamma)
    p = np.full(nx, p0)
    U = prim_to_cons(rho, v, p, gamma)

    # Reference horizon based on sigmaR=8 pressureless benchmark, t_c v/R~0.25.
    t_end = horizon_baseline_tc * (0.25/vs)
    t = 0.0
    pguess = p.copy()
    rho_max = 1.0
    cs_max = cs0
    v0_peak = float(np.max(v))

    while t < t_end:
        rho, v, p, cs = cons_to_prim(U, gamma, pguess)
        pguess = p
        rho_max = max(rho_max, float(np.max(rho)))
        cs_max = max(cs_max, float(np.max(cs)))
        char_plus = np.abs((v+cs)/(1.0+v*cs))
        char_minus = np.abs((v-cs)/(1.0-v*cs))
        maxspeed = max(float(np.max(char_plus)), float(np.max(char_minus)), 1e-8)
        dt = min(0.35*dx/maxspeed, t_end-t)

        Ug = np.pad(U, ((0,0),(2,2)), mode="edge")
        pg = np.pad(p, 2, mode="edge")
        primg = cons_to_prim(Ug, gamma, pg)
        UL, UR = Ug[:,:-1], Ug[:,1:]
        primL = tuple(z[:-1] for z in primg)
        primR = tuple(z[1:] for z in primg)
        FH = hll_flux(UL, UR, primL, primR)
        U = U - (dt/dx)*(FH[:,2:nx+2]-FH[:,1:nx+1])
        t += dt

    rho, v, p, cs = cons_to_prim(U, gamma, pguess)
    return Result(
        gamma=gamma,
        cs0=cs0,
        sigma_R=sigma_R,
        nx=nx,
        max_density_ratio=max(rho_max, float(np.max(rho))),
        peak_retention=float(np.max(v)/v0_peak),
        max_sound_speed=max(cs_max, float(np.max(cs))),
        max_abs_dv_dx=float(np.max(np.abs(np.gradient(v, dx)))),
        min_density=float(np.min(rho)),
        min_pressure=float(np.min(p)),
    )


def resolution_gate(low: Result, high: Result, gates: Gates) -> Dict[str, object]:
    grad_ratio = high.max_abs_dv_dx / max(low.max_abs_dv_dx, 1e-12)
    checks = {
        "density": high.max_density_ratio <= gates.density_ratio_max,
        "amplitude": high.peak_retention >= gates.peak_retention_min,
        "causality": high.max_sound_speed < gates.sound_speed_max,
        "shock_suspicion": grad_ratio <= gates.shock_gradient_ratio_max,
    }
    return {
        "checks": checks,
        "gradient_ratio_2N_over_N": grad_ratio,
        "pass": all(checks.values()),
        "claims_state": (
            "REDUCED_DYNAMICAL_SURVIVOR" if all(checks.values())
            else "REQUIRES_SOURCE_MODEL_IMPROVEMENT"
        ),
    }


def perturbation_ensemble_gate(
    gamma: float,
    cs0: float,
    sigma_R: float,
    gates: Gates,
    seeds: int = 20,
    perturbation: float = 0.05,
) -> Dict[str, object]:
    results = []
    for seed in range(1, seeds + 1):
        low = run_srhd(gamma, cs0, sigma_R, nx=400, perturbation=perturbation, seed=seed)
        high = run_srhd(gamma, cs0, sigma_R, nx=800, perturbation=perturbation, seed=seed)
        gate = resolution_gate(low, high, gates)
        results.append({
            "seed": seed,
            "high": asdict(high),
            "gate": gate,
        })
    pass_fraction = sum(1 for r in results if r["gate"]["pass"]) / len(results)
    return {
        "perturbation_fraction": perturbation,
        "seed_count": seeds,
        "pass_fraction": pass_fraction,
        "required_pass_fraction": gates.perturbation_pass_fraction_min,
        "pass": pass_fraction >= gates.perturbation_pass_fraction_min,
        "results": results,
    }


def default_campaign(gates: Gates) -> Dict[str, object]:
    candidates: List[Dict[str, object]] = []
    for sigma in (4.4, 4.8, 5.5, 6.5, 8.0):
        for cs0 in np.arange(0.16, 0.301, 0.02):
            low = run_srhd(2.0, float(cs0), sigma, nx=400)
            high = run_srhd(2.0, float(cs0), sigma, nx=800)
            gate = resolution_gate(low, high, gates)
            candidates.append({
                "sigma_R": sigma,
                "cs0": float(cs0),
                "low": asdict(low),
                "high": asdict(high),
                "gate": gate,
            })

    passed = [x for x in candidates if x["gate"]["pass"]]
    closest = min(
        candidates,
        key=lambda x: (
            max(0.0, x["high"]["max_density_ratio"]/gates.density_ratio_max - 1.0)
            + max(0.0, gates.peak_retention_min - x["high"]["peak_retention"])
            + max(0.0, x["gate"]["gradient_ratio_2N_over_N"]/gates.shock_gradient_ratio_max - 1.0)
        )
    )
    perturbation_gate = perturbation_ensemble_gate(
        2.0,
        float(closest["cs0"]),
        float(closest["sigma_R"]),
        gates,
        seeds=20,
        perturbation=0.05,
    )
    final_pass = bool(passed) and perturbation_gate["pass"]
    return {
        "schema": "WS-WARP-DYNAMICS-v1",
        "model": "1D_SRHD_gamma_law_HLL",
        "claims_limit": "Reduced screening only; no full-GR or propulsion claim.",
        "gates": asdict(gates),
        "candidate_count": len(candidates),
        "pass_count": len(passed),
        "closest_candidate": closest,
        "closest_candidate_perturbation_gate": perturbation_gate,
        "status": "PASS" if final_pass else "NO_FULL_PASS",
        "candidates": candidates,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="warp_campaign.json")
    ap.add_argument("--csv", default="warp_campaign.csv")
    args = ap.parse_args()

    gates = Gates()
    report = default_campaign(gates)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        fields = [
            "sigma_R","cs0","max_density_ratio","peak_retention",
            "max_sound_speed","gradient_ratio","pass","claims_state"
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in report["candidates"]:
            w.writerow({
                "sigma_R": c["sigma_R"],
                "cs0": c["cs0"],
                "max_density_ratio": c["high"]["max_density_ratio"],
                "peak_retention": c["high"]["peak_retention"],
                "max_sound_speed": c["high"]["max_sound_speed"],
                "gradient_ratio": c["gate"]["gradient_ratio_2N_over_N"],
                "pass": c["gate"]["pass"],
                "claims_state": c["gate"]["claims_state"],
            })

    print(json.dumps({
        "status": report["status"],
        "pass_count": report["pass_count"],
        "candidate_count": report["candidate_count"],
        "closest_candidate": report["closest_candidate"],
        "closest_candidate_perturbation_gate": {
            "pass_fraction": report["closest_candidate_perturbation_gate"]["pass_fraction"],
            "required_pass_fraction": report["closest_candidate_perturbation_gate"]["required_pass_fraction"],
            "pass": report["closest_candidate_perturbation_gate"]["pass"],
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
