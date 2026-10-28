"""Rolling, net-of-cost performance checks against a persisted benchmark.

Wilson intervals compare success probabilities (a win means net P/L > 0).
This is a monitoring heuristic: serial correlation, repeated monitoring and
different payoff sizes limit its statistical interpretation. A configurable
net expectancy floor independently catches loss despite stable hit rates.
Recommendations never approve/promote a strategy or mutate its lifecycle.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import sqlite3
from statistics import mean


@dataclass(frozen=True)
class Benchmark:
    strategy_id: str
    evidence_id: str
    sample_size: int
    wins: int
    mean_net_pnl: float


@dataclass(frozen=True)
class WatchdogPolicy:
    minimum_outcomes: int = 30
    rolling_window: int = 100
    wilson_z: float = 1.96
    permitted_win_rate_drop: float = 0.0
    net_expectancy_floor: float = 0.0


@dataclass(frozen=True)
class DegradationReport:
    strategy_id: str
    status: str
    recommend_suspend: bool
    reasons: tuple[str, ...]
    sample_size: int
    metrics: dict


def wilson_interval(wins: int, n: int, z: float = 1.96):
    if n < 1 or wins < 0 or wins > n or not math.isfinite(z) or z <= 0:
        raise ValueError('invalid Wilson inputs')
    p = wins / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


class DegradationWatchdog:
    def __init__(self, path, policy=WatchdogPolicy()):
        if (policy.minimum_outcomes < 2 or policy.rolling_window < policy.minimum_outcomes
                or not math.isfinite(policy.wilson_z) or policy.wilson_z <= 0
                or not 0 <= policy.permitted_win_rate_drop <= 1
                or not math.isfinite(policy.net_expectancy_floor)):
            raise ValueError('invalid watchdog policy')
        self.path, self.policy = str(path), policy
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS degradation_benchmarks '
                       '(strategy_id TEXT PRIMARY KEY, evidence TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS degradation_observations '
                       '(id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, report TEXT NOT NULL)')

    def register_benchmark(self, benchmark: Benchmark):
        """Call only after external evidence verification. Never auto-fit on live outcomes."""
        if (not benchmark.strategy_id or not benchmark.evidence_id
                or benchmark.sample_size < self.policy.minimum_outcomes
                or not 0 <= benchmark.wins <= benchmark.sample_size
                or not math.isfinite(benchmark.mean_net_pnl)):
            raise ValueError('valid independently verified benchmark required')
        encoded = json.dumps(asdict(benchmark), sort_keys=True, allow_nan=False)
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT evidence FROM degradation_benchmarks WHERE strategy_id=?',
                             (benchmark.strategy_id,)).fetchone()
            if row and row[0] != encoded:
                raise ValueError('benchmark is immutable; create a new strategy version')
            db.execute('INSERT OR IGNORE INTO degradation_benchmarks VALUES (?, ?)',
                       (benchmark.strategy_id, encoded))

    def benchmark(self, strategy_id):
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT evidence FROM degradation_benchmarks WHERE strategy_id=?',
                             (strategy_id,)).fetchone()
            return Benchmark(**json.loads(row[0])) if row else None

    def evaluate(self, strategy_id: str, net_outcomes) -> DegradationReport:
        """Outcomes must be chronological, completed, net of ALL costs, one per trade."""
        outcomes = list(net_outcomes)[-self.policy.rolling_window:]
        baseline = self.benchmark(strategy_id)
        if any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in outcomes):
            report = DegradationReport(strategy_id, 'INDETERMINATE', False, ('INVALID_NET_OUTCOMES',), len(outcomes), {})
        elif baseline is None:
            report = DegradationReport(strategy_id, 'INDETERMINATE', False, ('VERIFIED_BENCHMARK_MISSING',), len(outcomes), {})
        elif len(outcomes) < self.policy.minimum_outcomes:
            report = DegradationReport(strategy_id, 'INSUFFICIENT_SAMPLE', False, ('MINIMUM_OUTCOMES_NOT_MET',),
                                       len(outcomes), {'required': self.policy.minimum_outcomes})
        else:
            wins = sum(x > 0 for x in outcomes)
            observed_interval = wilson_interval(wins, len(outcomes), self.policy.wilson_z)
            reference_interval = wilson_interval(baseline.wins, baseline.sample_size, self.policy.wilson_z)
            net_mean = mean(outcomes)
            reasons = []
            if observed_interval[1] < reference_interval[0] - self.policy.permitted_win_rate_drop:
                reasons.append('WIN_RATE_BELOW_BENCHMARK_WILSON_INTERVAL')
            if net_mean < self.policy.net_expectancy_floor:
                reasons.append('ROLLING_NET_EXPECTANCY_BELOW_FLOOR')
            metrics = {'observed_wins': wins, 'observed_win_rate': wins / len(outcomes),
                       'observed_wilson_interval': observed_interval,
                       'benchmark_wilson_interval': reference_interval, 'rolling_net_mean': net_mean,
                       'benchmark_net_mean': baseline.mean_net_pnl, 'net_total': sum(outcomes),
                       'evidence_id': baseline.evidence_id,
                       'policy': asdict(self.policy), 'independent_outcomes_assumption': True}
            report = DegradationReport(strategy_id, 'DEGRADED' if reasons else 'NO_DEGRADATION_DETECTED',
                                       bool(reasons), tuple(reasons), len(outcomes), metrics)
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO degradation_observations(observed_at, report) VALUES (?, ?)',
                       (datetime.now(timezone.utc).isoformat(), json.dumps(asdict(report), allow_nan=False)))
        return report
