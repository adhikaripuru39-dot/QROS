from datetime import datetime, timezone
from types import SimpleNamespace as N
import pytest
from sqlalchemy import select
from qros.db.models import Strategy, Trade, SignalLog, EvidenceReport
from qros.db.session import session_scope
from qros.research.registry import signals
from qros.research.library import library
from qros.services.signal_log import record_signal
from qros.config.schemas import TradingMode

def create(client):
    r=client.post('/api/library/versions',json={'hypothesis_id':'momentum','symbol':'EURUSD'})
    assert r.status_code==201,r.text
    return r.json()['id']

def test_library_five_sources_and_causal_pullback():
    assert len(library())==5 and len({s['id'] for s in library()})==5
    assert all(s['sources'] and s['scaling_limits'] for s in library())
    bars=[{'time':1700000000+i*3600,'open':100+i*.1,'high':101+i*.1,
           'low':99+i*.1,'close':100+i*.1+(.7 if i%8==0 else -.4),'tick_volume':10} for i in range(100)]
    bars[80].update(close=106.,low=105.8)
    full=signals(bars,'trend_pullback')
    assert any(full)
    for n in [70,80,90]:assert signals(bars[:n],'trend_pullback')==full[:n]

def test_create_fork_preserves_original_and_clears_evidence(client):
    sid=create(client)
    with session_scope(client.app.state.session_factory) as db:
        parent=db.get(Strategy,sid);parent.status='ACTIVE'
        parent.spec={**parent.spec,'validation_report_id':'old-proof','paper_report_id':'old-paper'}
    r=client.post(f'/api/library/versions/{sid}/fork',json={'symbol':'EURUSD','reason':'Test a wider target to reduce turnover','target_atr_multiple':5})
    assert r.status_code==201,r.text
    child=r.json();assert child['status']=='IDEA' and child['spec']['parent_id']==sid
    assert child['spec']['runtime']['target_atr_multiple']==5
    assert 'validation_report_id' not in child['spec'] and 'paper_report_id' not in child['spec']
    assert client.get(f'/api/strategies/{sid}').json()['spec']['runtime']['target_atr_multiple']==3
    job=client.post(f"/api/library/versions/{child['id']}/research",json={}).json()
    payload=next(j for j in client.get('/api/research/jobs').json() if j['id']==job['id'])['payload']
    assert payload['strategy_id']==child['id'] and payload['runtime_spec']==child['spec']['runtime']
    assert payload['finalize_oos'] is False

def test_library_validation_auth_and_week_boundaries(client):
    assert client.post('/api/library/versions',json={'hypothesis_id':'momentum','symbol':'NOTCONFIGURED'}).status_code==422
    assert client.post('/api/library/versions',json={'hypothesis_id':'momentum','symbol':'EURUSD','atr_period':51}).status_code==422
    sid=create(client)
    assert client.get(f'/api/library/versions/{sid}/weekly?week_start=2026-10-20').status_code==422
    assert client.get('/api/library',headers={'Authorization':'Bearer wrong'}).status_code==401

def test_weekly_modes_nepal_boundary_net_costs_and_immutable_review(client):
    sid=create(client)
    def trade(key,exit_at,mode='paper'):
        return Trade(mode=mode,strategy_id=sid,symbol='EURUSD',side='buy',volume=.01,
            entry_time=datetime(2026,10,18,17,tzinfo=timezone.utc),entry_price=1.1,
            exit_time=datetime.fromisoformat(exit_at),exit_price=1.2,pnl=10.,commission=-2.,swap=-1.,
            risk_amount=5.,reason='fixture',exit_reason='target',client_order_id=key)
    with session_scope(client.app.state.session_factory) as db:
        db.add_all([trade('included','2026-10-18T18:15:00+00:00'),
                    trade('before','2026-10-18T18:14:59+00:00'),
                    trade('next-week','2026-10-25T18:15:00+00:00'),
                    trade('other-mode','2026-10-19T10:00:00+00:00','demo')])
    url=f'/api/library/versions/{sid}/weekly?week_start=2026-10-19&mode=paper'
    report=client.get(url).json()
    assert report['statistics']['n']==1 and report['net_pnl']==10 and report['mean_r']==2
    assert report['commission']==-2 and report['swap']==-1
    body={'week_start':'2026-10-19','notes':'Do not tune from one trade; collect more data',
          'decision':'collect_more_data','snapshot_hash':report['snapshot_hash']}
    saved=client.post(f'/api/library/versions/{sid}/reviews',json=body)
    assert saved.status_code==201,saved.text
    with session_scope(client.app.state.session_factory) as db:
        db.add(trade('later','2026-10-20T10:00:00+00:00'))
    assert client.post(f'/api/library/versions/{sid}/reviews',json=body).status_code==409
    reviews=client.get('/api/library/reviews').json()
    assert reviews[0]['snapshot']['net_pnl']==10
    assert client.get(url).json()['net_pnl']==20

def test_empty_week_has_no_fabricated_profit(client):
    sid=create(client)
    r=client.get(f'/api/library/versions/{sid}/weekly?week_start=2026-10-19').json()
    assert r['statistics']['n']==0 and r['net_pnl'] is None and r['mean_r'] is None
    assert r['interpretation']=='No forward evidence'

def test_signal_logs_deduplicate_bars_and_keep_modes_separate(factory):
    now=datetime(2026,10,24,tzinfo=timezone.utc)
    runtime=N(strategy_id='test',mode=TradingMode.PAPER)
    decision=N(completed_bar_at=now,reason='NO_SIGNAL',client_order_id=None)
    with session_scope(factory) as db:
        record_signal(db,runtime,decision,{},now);db.flush()
        record_signal(db,runtime,decision,{},now)
        runtime.mode=TradingMode.DEMO;record_signal(db,runtime,decision,{},now)
    with session_scope(factory) as db:assert len(list(db.execute(select(SignalLog)).scalars()))==2
