from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from qros.config.settings import Settings
from qros.db.models import (AuditLog, ControlState, EvidenceReport, OrderLedger, Strategy,
                            StrategyTransition, SystemState, Trade)
from qros.db.session import session_scope
from qros.research.runner import implementation_hash
from qros.services.degradation_service import evaluate_degradation
from qros.services.evidence import canonical_hash


NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
ACTIVATED = NOW - timedelta(days=2)


def seed(db):
    strategy = Strategy(id='s', hypothesis_id='momentum', family='Momentum', name='Observed candidate',
                        status='PAPER_TRADING', spec={'validation_report_id': 'validation'})
    db.add(strategy)
    db.add(ControlState(id=1, trading_mode='paper', run_state='running', kill_switch=False,
                        active_strategy_ids=['s', 'other']))
    db.add(SystemState(key='reconciliation', data={'account_key': 'current', 'clean': True}, updated_at=NOW))
    db.add(StrategyTransition(strategy_id='s', from_status='VALIDATED', to_status='PAPER_TRADING',
                             actor='owner', actor_kind='owner', evidence={}, criteria='Owner paper activation',
                             created_at=ACTIVATED))
    code = implementation_hash()
    config = canonical_hash({})
    content = {'binding': {'source_dataset_hash': 'a' * 64, 'code_hash': code, 'config_hash': config},
               'config': {}, 'eligible': True, 'selected_candidate': 'momentum',
               'oos': {'evaluated': True, 'holdout_hash': 'b' * 64,
                       'metrics': {'n': 100, 'win_rate': .8, 'expectancy': 1.0}}}
    report = EvidenceReport(id='validation', strategy_id='s', kind='validation', passed=True,
                            dataset_hash='a' * 64, code_hash=code, config_hash=config,
                            report_hash=canonical_hash(content), content=content)
    db.add(report)
    db.flush()
    return strategy, report


def trades(db, n, pnl, *, prefix='paper', mode='paper', account='current', entry=None,
           exit_time=NOW - timedelta(hours=1), costs=0):
    for i in range(n):
        cid = prefix + str(i)
        db.add(OrderLedger(client_order_id=cid, account_key=account, strategy_id='s', symbol='EURUSD',
                           mode=mode, status='closed', request={}))
        db.add(Trade(client_order_id=cid, mode=mode, strategy_id='s', symbol='EURUSD', side='buy', volume=.1,
                     entry_time=entry or NOW - timedelta(days=1), entry_price=1.1, exit_time=exit_time,
                     exit_price=1.11, pnl=pnl, commission=costs, swap=costs, reason='Observed market signal'))
    db.flush()


def settings(tmp_path):
    return Settings(data_dir=tmp_path / 'data', _env_file=None)


def test_verified_degradation_suspends_once_and_removes_active_selection(factory, tmp_path):
    with session_scope(factory) as db:
        strategy, _ = seed(db)
        trades(db, 30, -10)
        result = evaluate_degradation(db, settings(tmp_path), NOW)
        assert result[0]['status'] == 'DEGRADED' and result[0]['recommend_suspend']
        assert strategy.status == 'SUSPENDED'
        assert db.get(ControlState, 1).active_strategy_ids == ['other']
        count = db.scalar(select(func.count()).select_from(StrategyTransition))
        assert count == 2
        assert evaluate_degradation(db, settings(tmp_path), NOW + timedelta(seconds=1)) == []
        assert db.scalar(select(func.count()).select_from(StrategyTransition)) == count
        suspended = db.execute(select(StrategyTransition).where(StrategyTransition.to_status == 'SUSPENDED')).scalar_one()
        assert suspended.actor_kind == 'system' and suspended.evidence['validation_report_id'] == 'validation'


def test_repeat_same_outcomes_idempotent_and_net_pnl_not_double_charged(factory, tmp_path):
    with session_scope(factory) as db:
        strategy, _ = seed(db)
        trades(db, 30, 1, costs=-100)
        first = evaluate_degradation(db, settings(tmp_path), NOW)[0]
        assert first['status'] == 'NO_DEGRADATION_DETECTED'
        assert first['metrics']['rolling_net_mean'] == 1
        observations = db.scalar(select(func.count()).select_from(AuditLog))
        first_updated = db.get(SystemState, 'degradation:s').updated_at
        again = evaluate_degradation(db, settings(tmp_path), NOW + timedelta(seconds=1))[0]
        assert again['observation_signature'] == first['observation_signature']
        assert db.get(SystemState, 'degradation:s').updated_at == first_updated
        assert db.scalar(select(func.count()).select_from(AuditLog)) == observations
        assert strategy.status == 'PAPER_TRADING'


def test_mode_account_activation_and_closed_outcomes_are_scoped(factory, tmp_path):
    with session_scope(factory) as db:
        seed(db)
        trades(db, 29, 1)
        trades(db, 40, -100, prefix='wrongmode', mode='demo')
        trades(db, 40, -100, prefix='wrongaccount', account='other')
        trades(db, 40, -100, prefix='oldactivation', entry=ACTIVATED - timedelta(days=1))
        trades(db, 40, -100, prefix='open', exit_time=None)
        trades(db, 40, -100, prefix='future', exit_time=NOW + timedelta(days=1))
        result = evaluate_degradation(db, settings(tmp_path), NOW)[0]
        assert result['sample_size'] == 29 and result['status'] == 'INSUFFICIENT_SAMPLE'
        assert not result['recommend_suspend']


def test_tampered_evidence_is_indeterminate_not_healthy(factory, tmp_path):
    with session_scope(factory) as db:
        strategy, report = seed(db)
        report.content = {**report.content, 'eligible': False}
        trades(db, 40, 10)
        result = evaluate_degradation(db, settings(tmp_path), NOW)[0]
        assert result['status'] == 'INDETERMINATE'
        assert 'EVIDENCE_HASH_MISMATCH' in result['reasons']
        assert not result['recommend_suspend'] and strategy.status == 'PAPER_TRADING'


def test_missing_owner_activation_is_indeterminate(factory, tmp_path):
    with session_scope(factory) as db:
        seed(db)
        activation = db.execute(select(StrategyTransition)).scalar_one()
        activation.actor_kind = 'system'
        result = evaluate_degradation(db, settings(tmp_path), NOW)[0]
        assert result['status'] == 'INDETERMINATE'
        assert 'OWNER_FORWARD_ACTIVATION_MISSING' in result['reasons']


def test_baseline_cannot_be_silently_refit_from_changed_report(factory, tmp_path):
    with session_scope(factory) as db:
        _, report = seed(db)
        trades(db, 30, 1)
        assert evaluate_degradation(db, settings(tmp_path), NOW)[0]['status'] == 'NO_DEGRADATION_DETECTED'
        report.content = {**report.content, 'oos': {**report.content['oos'],
                         'metrics': {'n': 100, 'win_rate': .7, 'expectancy': .5}}}
        report.report_hash = canonical_hash(report.content)
        result = evaluate_degradation(db, settings(tmp_path), NOW)[0]
        assert result['status'] == 'INDETERMINATE'
        assert any('benchmark is immutable' in r for r in result['reasons'])
