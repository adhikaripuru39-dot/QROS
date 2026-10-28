import pytest

from qros.monitoring.degradation import Benchmark, DegradationWatchdog, WatchdogPolicy, wilson_interval


def test_wilson_boundary_behavior():
    low, high = wilson_interval(0, 100)
    assert low == pytest.approx(0) and 0 < high < .04
    low, high = wilson_interval(100, 100)
    assert .96 < low < 1 and high == pytest.approx(1)


def test_sample_threshold_and_persistent_immutable_benchmark(tmp_path):
    path = tmp_path / 'watch.sqlite'
    d = DegradationWatchdog(path)
    baseline = Benchmark('s', 'verified-report-sha256', 200, 150, 1.0)
    d.register_benchmark(baseline)
    assert not d.evaluate('s', [-10] * 29).recommend_suspend
    restarted = DegradationWatchdog(path)
    assert restarted.benchmark('s') == baseline
    with pytest.raises(ValueError):
        restarted.register_benchmark(Benchmark('s', 'new-report', 200, 120, .1))
    r = restarted.evaluate('s', [-10] * 30)
    assert r.recommend_suspend and r.status == 'DEGRADED'
    assert 'WIN_RATE_BELOW_BENCHMARK_WILSON_INTERVAL' in r.reasons
    assert 'ROLLING_NET_EXPECTANCY_BELOW_FLOOR' in r.reasons


def test_win_rate_can_degrade_despite_positive_mean(tmp_path):
    d = DegradationWatchdog(tmp_path / 'watch.sqlite')
    d.register_benchmark(Benchmark('s', 'evidence', 500, 450, 1))
    r = d.evaluate('s', [100, -1, -1, -1, -1] * 10)
    assert r.recommend_suspend
    assert r.metrics['rolling_net_mean'] > 0


def test_high_win_rate_does_not_hide_negative_net_expectancy(tmp_path):
    d = DegradationWatchdog(tmp_path / 'watch.sqlite')
    d.register_benchmark(Benchmark('s', 'evidence', 100, 90, 1))
    r = d.evaluate('s', [1] * 90 + [-100] * 10)
    assert r.recommend_suspend and r.reasons == ('ROLLING_NET_EXPECTANCY_BELOW_FLOOR',)


def test_missing_or_invalid_outcomes_indeterminate_not_approved(tmp_path):
    d = DegradationWatchdog(tmp_path / 'watch.sqlite', WatchdogPolicy(rolling_window=30))
    assert d.evaluate('s', [1] * 30).status == 'INDETERMINATE'
    d.register_benchmark(Benchmark('s', 'evidence', 100, 60, 1))
    assert d.evaluate('s', [float('nan')] * 30).status == 'INDETERMINATE'
    r = d.evaluate('s', [-100] * 100 + [1] * 30)
    assert r.status == 'NO_DEGRADATION_DETECTED' and r.sample_size == 30
