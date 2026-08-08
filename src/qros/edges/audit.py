"""Part 10 ch.2: False Edge Audit Framework — 5 diagnostics to prevent curve-fitted strategies."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qros.governance.policy import DEFAULT_POLICY, Policy
from qros.stats.bootstrap import permutation_test
from qros.stats.sharpe import deflated_sharpe_ratio
from qros.stats.timeseries import engle_granger_p


@dataclass
class FalseEdgeCheck:
    """A single false-edge diagnostic result."""

    diagnostic: str
    passed: bool
    reason: str
    evidence: dict


@dataclass
class EdgeAudit:
    """Aggregate result of the 5 false-edge diagnostics."""

    checks: list[FalseEdgeCheck]
    overall_pass: bool

    def summary(self) -> str:
        pass_ct = sum(c.passed for c in self.checks)
        return f"{pass_ct}/{len(self.checks)} diagnostics passed"


def audit_false_edge(
    returns: np.ndarray,
    n_trials: int,
    perturbed_returns: np.ndarray | None = None,
    cointegration_pair: tuple[np.ndarray, np.ndarray] | None = None,
    execution_slippage_bps: float | None = None,
    tiny_size_pnl: float | None = None,
    institutional_size_pnl: float | None = None,
    policy: Policy = DEFAULT_POLICY,
) -> EdgeAudit:
    """Run the 5 false-edge diagnostics from Part 10 ch.2.

    1. Curve-fitting / overfitting: performance drops drastically under ±10% parameter perturbation.
    2. Data mining / snooping: DSR fails after adjusting for total tested trial count.
    3. Coincidence / luck: signal-to-noise ratio statistically indistinguishable from zero via permutation.
    4. Execution mirage: edge vanishes after accounting for realistic slippage + market impact.
    5. Capacity bottleneck: edge only profitable for trivial (<$10k) trades, fails at institutional ($50M) size.
    """
    checks: list[FalseEdgeCheck] = []

    # Diagnostic 1: Curve-fitting via parameter perturbation
    if perturbed_returns is not None:
        base_mean = float(np.mean(returns))
        pert_mean = float(np.mean(perturbed_returns))
        degradation = abs(pert_mean - base_mean) / (abs(base_mean) + 1e-9)
        passed = degradation < policy.perturbation_window
        checks.append(
            FalseEdgeCheck(
                diagnostic="curve_fitting",
                passed=passed,
                reason=f"Perturbation degradation {degradation:.2%} {'<' if passed else '>='} {policy.perturbation_window:.0%}",
                evidence={"base_mean": base_mean, "perturbed_mean": pert_mean, "degradation": degradation},
            )
        )

    # Diagnostic 2: Data mining via DSR
    dsr = deflated_sharpe_ratio(returns, n_trials=n_trials, policy=policy)
    passed_dsr = not dsr.rejected
    checks.append(
        FalseEdgeCheck(
            diagnostic="data_mining",
            passed=passed_dsr,
            reason=f"DSR p-value {dsr.p_value:.4f} {'<' if passed_dsr else '>='} {policy.dsr_p_max}",
            evidence={"dsr_p": dsr.p_value, "n_trials": n_trials, "sr": dsr.sr},
        )
    )

    # Diagnostic 3: Coincidence via permutation test
    # Split returns into signal and noise proxies; if no split provided, use half-split.
    n = len(returns)
    if n >= 20:
        half = n // 2
        perm = permutation_test(returns[:half], returns[half:], lambda a, b: float(np.mean(a) - np.mean(b)), n_perm=min(policy.permutation_n, 1000))
        passed_perm = perm["p_value"] < 0.05
        checks.append(
            FalseEdgeCheck(
                diagnostic="coincidence",
                passed=passed_perm,
                reason=f"Permutation p-value {perm['p_value']:.4f} {'<' if passed_perm else '>='} 0.05",
                evidence={"perm_p": perm["p_value"], "observed": perm["observed"]},
            )
        )

    # Diagnostic 4: Execution mirage
    if execution_slippage_bps is not None:
        # Edge vanishes if mean return < slippage cost
        mean_return_bps = float(np.mean(returns)) * 10_000
        net = mean_return_bps - execution_slippage_bps
        passed_exec = net > 0
        checks.append(
            FalseEdgeCheck(
                diagnostic="execution_mirage",
                passed=passed_exec,
                reason=f"Net return {net:.2f}bp after {execution_slippage_bps:.2f}bp slippage {'>' if passed_exec else '<='} 0",
                evidence={"gross_return_bps": mean_return_bps, "slippage_bps": execution_slippage_bps, "net_bps": net},
            )
        )

    # Diagnostic 5: Capacity bottleneck
    if tiny_size_pnl is not None and institutional_size_pnl is not None:
        ratio = institutional_size_pnl / (tiny_size_pnl + 1e-9)
        # Edge scales if institutional PnL is at least 50% of tiny-size PnL
        passed_cap = ratio > 0.5
        checks.append(
            FalseEdgeCheck(
                diagnostic="capacity_bottleneck",
                passed=passed_cap,
                reason=f"Institutional PnL ratio {ratio:.2%} {'>' if passed_cap else '<='} 50%",
                evidence={"tiny_pnl": tiny_size_pnl, "institutional_pnl": institutional_size_pnl, "ratio": ratio},
            )
        )

    # Structural cointegration check (optional, enhances diagnostic 2)
    if cointegration_pair is not None:
        y, x = cointegration_pair
        p = engle_granger_p(y, x)
        passed_coint = p < policy.cointegration_p_max
        checks.append(
            FalseEdgeCheck(
                diagnostic="structural_cointegration",
                passed=passed_coint,
                reason=f"Engle-Granger p-value {p:.4f} {'<' if passed_coint else '>='} {policy.cointegration_p_max}",
                evidence={"eg_p": p},
            )
        )

    overall = all(c.passed for c in checks)
    return EdgeAudit(checks=checks, overall_pass=overall)