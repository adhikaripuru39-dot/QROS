"""Verified forward-performance monitoring; system may suspend, never approve."""
from dataclasses import asdict
from datetime import datetime, timezone
import math
from pathlib import Path
import sqlite3

from sqlalchemy import select

from qros.audit.log import record
from qros.db.models import ControlState, OrderLedger, Strategy, StrategyTransition, SystemState, Trade
from qros.governance.lifecycle import StrategyStatus, check_transition
from qros.monitoring.degradation import Benchmark, DegradationWatchdog, WatchdogPolicy
from qros.services.evidence import canonical_hash, verify_report
from qros.services.settings_store import as_utc


DEPLOYED = ('PAPER_TRADING', 'DEMO_APPROVED', 'LIVE_APPROVED', 'ACTIVE')
ACTIVATION = {'paper': ('PAPER_TRADING',), 'demo': ('DEMO_APPROVED',),
              'live': ('LIVE_APPROVED', 'ACTIVE')}


def _baseline(strategy, report):
    metrics = report.content.get('oos', {}).get('metrics', {})
    n, win_rate, expectancy = metrics.get('n'), metrics.get('win_rate'), metrics.get('expectancy')
    if (not isinstance(n, int) or isinstance(n, bool) or n < 1
            or not isinstance(win_rate, (int, float)) or not math.isfinite(win_rate) or not 0 <= win_rate <= 1
            or not isinstance(expectancy, (int, float)) or not math.isfinite(expectancy)):
        raise ValueError('VALIDATED_OOS_BENCHMARK_METRICS_INVALID')
    wins = round(n * win_rate)
    if not math.isclose(wins, n * win_rate, abs_tol=1e-6):
        raise ValueError('VALIDATED_OOS_WIN_COUNT_INCONSISTENT')
    return Benchmark(strategy.id, report.id + ':' + report.report_hash, n, wins, expectancy)


def evaluate_degradation(db, settings, now=None):
    """Inside the executor transaction, after reconciliation; safe to call repeatedly.

    One row per closed, reconciled forward trade, account/mode/activation scoped.
    The independent baseline store is immutable, so a changed benchmark requires
    a new strategy version. Repeated observations do not produce repeated writes.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('aware monitoring clock required')
    control = db.get(ControlState, 1)
    mode = control.trading_mode if control else 'off'
    reconciliation = db.get(SystemState, 'reconciliation')
    account = reconciliation.data.get('account_key') if reconciliation else None
    policy = WatchdogPolicy(
        minimum_outcomes=getattr(settings, 'degradation_minimum_outcomes', 30),
        rolling_window=getattr(settings, 'degradation_rolling_window', 100),
        wilson_z=getattr(settings, 'degradation_wilson_z', 1.96),
        permitted_win_rate_drop=getattr(settings, 'degradation_permitted_win_rate_drop', 0.0),
        net_expectancy_floor=getattr(settings, 'degradation_net_expectancy_floor', 0.0))
    watchdog = None
    reports = []
    for strategy in db.execute(select(Strategy).where(Strategy.status.in_(DEPLOYED))).scalars():
        key = 'degradation:' + strategy.id
        previous = db.get(SystemState, key)
        report_id = strategy.spec.get('validation_report_id', '')
        try:
            evidence, errors = verify_report(db, report_id, strategy.id, 'validation')
        except (ValueError, TypeError, KeyError, ArithmeticError):
            evidence, errors = None, ['EVIDENCE_CONTENT_INVALID']
        errors = list(errors)
        activation = None
        trades = []
        baseline = None
        if mode not in ACTIVATION:
            errors.append('FORWARD_MODE_INACTIVE')
        else:
            activation = db.execute(select(StrategyTransition).where(
                StrategyTransition.strategy_id == strategy.id,
                StrategyTransition.to_status.in_(ACTIVATION[mode]),
                StrategyTransition.actor_kind == 'owner').order_by(
                    StrategyTransition.created_at.desc(), StrategyTransition.id.desc()).limit(1)).scalar_one_or_none()
            if activation is None or as_utc(activation.created_at) > now:
                errors.append('OWNER_FORWARD_ACTIVATION_MISSING')
            if not account:
                errors.append('RECONCILED_ACCOUNT_SCOPE_UNKNOWN')
            if (not reconciliation or not reconciliation.data.get('clean')
                    or not 0 <= (now - as_utc(reconciliation.updated_at)).total_seconds() <= settings.stale_after_seconds):
                errors.append('RECONCILIATION_NOT_CURRENT_AND_CLEAN')
        if evidence is not None and not errors:
            try:
                baseline = _baseline(strategy, evidence)
            except ValueError as exc:
                errors.append(str(exc))
        if not errors:
            trades = list(db.execute(select(Trade).join(OrderLedger, OrderLedger.client_order_id == Trade.client_order_id).where(
                Trade.strategy_id == strategy.id, Trade.mode == mode,
                OrderLedger.account_key == account, OrderLedger.mode == mode,
                OrderLedger.strategy_id == strategy.id, OrderLedger.status == 'closed',
                Trade.entry_time >= activation.created_at, Trade.exit_time.is_not(None),
                Trade.exit_time <= now).order_by(Trade.exit_time.desc(), Trade.id.desc()).limit(policy.rolling_window)).scalars())
            trades.reverse()
            if any(t.pnl is None or not isinstance(t.pnl, (int, float)) or not math.isfinite(t.pnl)
                   or as_utc(t.exit_time) < as_utc(t.entry_time) for t in trades):
                errors.append('COMPLETED_NET_OUTCOME_INVALID')
        signature = canonical_hash({'mode': mode, 'account_key': account,
            'activation': activation.id if activation else None,
            'report': evidence.report_hash if evidence else report_id,
            'baseline': asdict(baseline) if baseline else None, 'errors': sorted(set(errors)),
            'policy': asdict(policy), 'outcomes': [[t.id, t.client_order_id, str(t.pnl), str(t.exit_time)] for t in trades]})
        if previous is not None and previous.data.get('observation_signature') == signature:
            reports.append(previous.data)
            continue
        if errors:
            data = {'strategy_id': strategy.id, 'status': 'INDETERMINATE', 'recommend_suspend': False,
                    'reasons': sorted(set(errors)), 'sample_size': len(trades), 'metrics': {}}
        else:
            try:
                if watchdog is None:
                    directory = Path(settings.data_dir) / 'monitoring'
                    directory.mkdir(parents=True, exist_ok=True)
                    watchdog = DegradationWatchdog(directory / 'degradation.sqlite', policy)
                watchdog.register_benchmark(baseline)
                data = asdict(watchdog.evaluate(strategy.id, [t.pnl for t in trades]))
            except (ValueError, OSError, sqlite3.Error) as exc:
                data = {'strategy_id': strategy.id, 'status': 'INDETERMINATE', 'recommend_suspend': False,
                        'reasons': ['BENCHMARK_MONITORING_UNAVAILABLE:' + str(exc)], 'sample_size': len(trades), 'metrics': {}}
        data.update({'observation_signature': signature, 'mode': mode, 'account_key': account,
                     'activation_id': activation.id if activation else None,
                     'evidence_id': report_id, 'observed_at': now.isoformat(),
                     'net_cost_convention': 'Trade.pnl is already net of commission, swap and fee'})
        if previous is None:
            db.add(SystemState(key=key, data=data, updated_at=now))
        else:
            previous.data, previous.updated_at = data, now
        if data['recommend_suspend']:
            reason = ';'.join(data['reasons'])
            rule = check_transition(StrategyStatus(strategy.status), StrategyStatus.SUSPENDED, 'system', {'reason': reason})
            old = strategy.status
            strategy.status, strategy.updated_at = 'SUSPENDED', now
            control.active_strategy_ids = [sid for sid in control.active_strategy_ids if sid != strategy.id]
            control.updated_at = now
            db.add(StrategyTransition(strategy_id=strategy.id, from_status=old, to_status='SUSPENDED',
                                     actor='degradation_watchdog', actor_kind='system',
                                     evidence={'reason': reason, 'observation_signature': signature,
                                               'validation_report_id': report_id},
                                     criteria=rule.criteria, created_at=now))
            record(db, 'degradation_watchdog', 'strategy.degradation.suspended', data)
        else:
            record(db, 'degradation_watchdog', 'strategy.degradation.observed', data)
        reports.append(data)
    return reports
