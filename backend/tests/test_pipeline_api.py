"""Readiness/job API contracts exercise actual isolated DB and owner auth."""
def test_pipeline_views_truthfully_block_without_observations(client):
    result=client.get('/api/system/readiness')
    assert result.status_code==200
    data=result.json()
    assert not data['ready_for_demo'] and not data['ready_for_live']
    assert 'executor_online' in data['blockers']
    assert 'verified_firm_profile' in data['blockers']
    assert 'risk_anchor_verified' in data['blockers']
    assert len(client.get('/api/research/hypotheses').json())==11
    assert client.get('/api/execution/orders').json()==[]

def test_jobs_are_queued_and_not_executed_by_api(client):
    response=client.post('/api/research/jobs',json={'symbol':'EURUSD','days':180,'timeframe':'M15'})
    assert response.status_code==202
    jobs=client.get('/api/research/jobs').json()
    assert jobs[0]['status']=='queued'
    assert client.get('/api/research/experiments').json()==[]
    assert client.post('/api/research/jobs',json={'symbol':'EURUSD','finalize_oos':True}).status_code==422

def test_hypothesis_registration_does_not_approve(client):
    response=client.post('/api/strategies/register',json={'hypothesis_id':'momentum','symbol':'EURUSD'})
    assert response.status_code==201 and response.json()['status']=='IDEA'
    sid=response.json()['id']
    assert client.post('/api/strategies/'+sid+'/transition',json={'target':'ACTIVE'}).status_code==422
    assert client.post('/api/strategies/register',json={'hypothesis_id':'unknown','symbol':'EURUSD'}).status_code==422

def test_pipeline_requires_owner(client):
    client.headers.clear()
    for path in ('/api/system/readiness','/api/execution/orders','/api/data/datasets','/api/research/jobs','/api/research/hypotheses'):
        assert client.get(path).status_code==401

def test_url_tokens_do_not_authenticate_stream_or_export(client):
    client.headers.clear()
    assert client.get('/api/journal/export.csv?token=test-owner-secret').status_code==401
    assert client.get('/api/stream?token=test-owner-secret').status_code==401
