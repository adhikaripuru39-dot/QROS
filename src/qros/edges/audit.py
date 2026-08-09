"""Part 10 ch.2: False Edge Audit Framework — mandatory 5-diagnostic contract.

Every call to ``audit_false_edge`` must return all five required diagnostics:

    1. curve_fitting      — parameter-perturbation robustness (±10% window)
    2. data_mining        — Deflated Sharpe Ratio adjusted for trial count
    3. coincidence        — permutation-test signal-to-noise
    4. execution_mirage   — edge survives realistic slippage + market impact
    5. capacity_bottleneck— edge scales to institutional size

If required evidence for a diagnostic is absent (e.g. no slippage or no PnL
evidence supplied), that diagnostic is returned with ``passed=False`` and an
explicit "insufficient evidence / not assessed" reason. The overall audit
passes **only if all five mandatory diagnostics pass**.

A sixth, purely supplementary diagnostic (``structural_cointegration``) may be
included when cointegration evidence is supplied; it never replaces or
suppresses any required diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qros.governance.policy import DEFAULT_POLICY, Policy
from qros.stats.bootstrap import permutation_test
from qros.stats.sharpe import deflated_sharpe_ratio
from qros.stats.timeseries import engle_granger_p

# The five mandatory Part 10 ch.2 diagnostics.
REQUIRED_DIAGNOSTICS: tuple[str, ...] = (
    "curve_fitting",
    "data_mining",
    "coincidence",
    "execution_mirage",
    "capacity_bottleneck",
)

INSUFFICIENT_REASON = "insufficient evidence / not assessed"


@dataclass
class FalseEdgeCheck:
    """A single false-edge diagnostic result."""

    diagnostic: str
    passed: bool
    reason: str
    evidence: dict


@dataclass
class EdgeAudit:
    """Aggregate result of the (mandatory 5 + optional) false-edge diagnostics."""

    checks: list[FalseEdgeCheck]
    overall_pass: bool

    def mandatory_checks(self) -> list[FalseEdgeCheck]:
        return [c for c in self.checks if c.diagnostic in REQUIRED_DIAGNOSTICS]

    def mandatory_passed_count(self) -> int:
        return sum(c.passed for c in self.mandatory_checks())

    def summary(self) -> str:
        return (
            f"{self.mandatory_passed_count()}/{len(REQUIRED_DIAGNOSTICS)} "
            f"mandatory diagnostics passed"
        )


def _insufficient(diagnostic: str, missing: str) -> FalseEdgeCheck:
    return FalseEdgeCheck(
        diagnostic=diagnostic,
        passed=False,
        reason=f"{INSUFFICIENT_REASON}: {missing} not provided",
        evidence={"missing": missing},
    )


def audit_false_edge(
    returns: np.ndarray,
    n_trials: int,
    perturbed_returns: np.ndarray | None = None,
    execution_slippage_bps: float | None = None,
    tiny_size_pnl: float | None = None,
    institutional_size_pnl: float | None = None,
    cointegration_pair: tuple[np.ndarray, np.ndarray] | None = None,
    policy: Policy = DEFAULT_POLICY,
) -> EdgeAudit:
    """Run the five mandatory false-edge diagnostics (Part 10 ch.2).

    Fail-closed contract: any diagnostic whose evidence is absent (not assessed)
    is set to ``passed=False`` and blocks the overall audit.
    """
    checks: list[FalseEdgeCheck] = []

    # ----- Diagnostic 1: Curve-fitting via parameter perturbation -----
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
    else:
        checks.append(_insufficient("curve_fitting", "perturbed_returns"))

    # ----- Diagnostic 2: Data mining (DSR adjusted for trial count) -----
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

    # ----- Diagnostic 3: Coincidence via permutation test -----
    n = len(returns)
    if n >= 20:
        half = n // 2
        perm = permutation_test(
            returns[:half], returns[half:],
            lambda a, b: float(np.mean(a) - np.mean(b)),
            n_perm=min(policy.permutation_n, 1000),
        )
        passed_perm = perm["p_value"] < 0.05
        checks.append(
            FalseEdgeCheck(
                diagnostic="coincidence",
                passed=passed_perm,
                reason=f"Permutation p-value {perm['p_value']:.4f} {'<' if passed_perm else '>='} 0.05",
                evidence={"perm_p": perm["p_value"], "observed": perm["observed"]},
            )
        )
    else:
        checks.append(_insufficient("coincidence", "at least 20 observations"))

    # ----- Diagnostic 4: Execution mirage -----
    if execution_slippage_bps is not None:
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
    else:
        checks.append(_insufficient("execution_mirage", "execution_slippage_bps"))

    # ----- Diagnostic 5: Capacity bottleneck (fail-closed on absent PnL evidence) -----
    capacity_evidence = (
        tiny_size_pnl is not None and institutional_size_pnl is not None
    )
    if capacity_evidence:
        ratio = institutional_size_pnl / (tiny_size_pnl + 1e-9)
        passed_cap = ratio > 0.5
        checks.append(
            FalseEdgeCheck(
                diagnostic="capacity_bottleneck",
                passed=passed_cap,
                reason=f"Institutional PnL ratio {ratio:.2%} {'>' if passed_cap else '<='} 50%",
                evidence={"tiny_pnl": tiny_size_pnl, "institutional_pnl": institutional_size_pnl, "ratio": ratio},
            )
        )
    else:
        checks.append(_insufficient("capacity_bottleneck", "tiny_size_pnl and institutional_size_pnl"))

    # ----- Optional supplementary diagnostic (never replaces the five above) -----
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

    mandatory = [c for c in checks if c.diagnostic in REQUIRED_DIAGNOSTICS]
    overall = len(mandatory) == len(REQUIRED_DIAGNOSTICS) and all(c.passed for c in mandatory)
    return EdgeAudit(checks=checks, overall_pass=overall)