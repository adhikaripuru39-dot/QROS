import pytest
from qros.api.app import create_app
from qros.config.settings import Settings

@pytest.mark.parametrize('path',['overview','risk/state','instruments','equity-curve','journal/stats','strategies','control/state','research/status','audit/verify'])
def test_read_endpoints(client,path):assert client.get('/api/'+path).status_code==200

def test_disconnected_states(client):
    overview=client.get('/api/overview').json()
    assert overview['account']=={'available':False,'stale':True}
    assert overview['pnl']['daily'] is None
    assert overview['open_positions'] is None
    assert client.get('/api/risk/state').json()['data'] is None
    assert not client.get('/api/journal/stats').json()['available']
    assert client.get('/api/equity-curve').json()['points']==[]

def test_auth_required(client):
    client.headers.clear()
    assert client.get('/api/overview').status_code==401
    assert client.post('/api/control/commands',json={'command':'stop'}).status_code==401
    assert client.get('/api/health').status_code==200

def test_command_is_only_queued(client):
    response=client.post('/api/control/commands',json={'command':'stop','wait_seconds':0})
    assert response.status_code==200 and response.json()['status']=='pending'
    assert client.get('/api/control/state').json()['run_state']=='stopped'
    assert client.get('/api/audit/verify').json()['ok']

def test_kill_and_live_typed_confirmations(client):
    for body in [{'command':'kill'},{'command':'set_mode','payload':{'mode':'live'}}]:
        assert client.post('/api/control/commands',json=body).status_code==422
    assert client.post('/api/control/commands',json={'command':'kill','confirm':'KILL','wait_seconds':0}).json()['status']=='pending'

def test_limits_validation_and_rollback(client):
    old=client.get('/api/limits').json();bad={**old,'daily_stop_pct':6,'max_total_open_risk_pct':1}
    assert client.post('/api/risk/validate',json={'limits':bad}).json()['ok'] is False
    assert client.put('/api/limits',json=bad).status_code==422
    assert client.get('/api/limits').json()==old

def test_atomic_risk_pair(client):
    state=client.get('/api/risk/state').json()
    body={'firm':state['firm'],'limits':state['limits']}
    assert client.put('/api/risk/configuration',json=body).status_code==200
    body['limits']['total_stop_pct']=99
    assert client.put('/api/risk/configuration',json=body).status_code==422
    assert client.get('/api/limits').json()['total_stop_pct']==7
    assert client.get('/api/audit/verify').json()['ok']

def test_research_preference(client):
    assert client.get('/api/research/profile').json()['profile']=='B'
    assert client.put('/api/research/profile',json={'profile':'C'}).status_code==200
    assert client.get('/api/research/profile').json()['profile']=='C'
    assert client.put('/api/research/profile',json={'profile':'D'}).status_code==422
    assert client.post('/api/research/jobs').status_code==422
    assert client.post('/api/research/jobs',json={'symbol':'EURUSD'}).status_code==202

def test_csv(client):
    response=client.get('/api/journal/export.csv')
    assert response.status_code==200 and response.text.startswith('id,mode,')

def test_production_token_required():
    with pytest.raises(ValueError):create_app(Settings(env='prod',api_token='change-me',_env_file=None))
