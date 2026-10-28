from datetime import datetime,timezone,timedelta
import json
from qros.risk.news import news_state,configured_news
from qros.config.settings import Settings,load_firm_profiles

NOW=datetime(2026,10,20,12,tzinfo=timezone.utc)

def snapshot():
    utc=int(NOW.timestamp());server=utc+10800
    return {'schema':2,'source':'mt5_builtin_calendar','read_only':True,'complete':True,'errors':0,
        'generated_utc':utc,'finished_utc':utc+1,'server_time':server,'server':'FTMO-Demo',
        'query_from_server':server-86400,'query_until_server':server+7*86400,
        'currencies':['USD','EUR','GBP','JPY','CHF','CAD','AUD'],
        'events':[{'id':'1','name':'Fixture release','currency':'USD','importance':3,
                   'time_server':server+300,'exact_time':True}]}

def check(tmp_path,raw=None,currencies=None,now=NOW,**kwargs):
    p=tmp_path/'calendar.json';p.write_text(json.dumps(raw or snapshot()))
    return news_state(p,now,currencies or {'EUR','USD'},5,5,
        expected_server='FTMO-Demo',expected_offset=10800,require_native=True,**kwargs)

def test_blackout_boundary_currency_and_gold(tmp_path):
    assert check(tmp_path)==(True,True,'NEWS_BLACKOUT')
    assert check(tmp_path,currencies={'XAU','USD'})[1]
    assert check(tmp_path,currencies={'EUR','GBP'})==(True,False,'OK')
    raw=snapshot();raw['events'][0]['time_server']+=1
    assert check(tmp_path,raw)==(True,False,'OK')
    raw['events'][0]['time_server']=raw['server_time']-300
    assert check(tmp_path,raw)[1]

def test_no_events_is_valid_only_after_successful_complete_query(tmp_path):
    raw=snapshot();raw['events']=[]
    assert check(tmp_path,raw)==(True,False,'OK')
    raw['complete']=False
    assert check(tmp_path,raw)[0] is False
    raw['complete']=True;raw['errors']=5400
    assert check(tmp_path,raw)[0] is False

def test_stale_future_and_slow_capture_fail_closed(tmp_path):
    assert check(tmp_path,now=NOW+timedelta(seconds=121))[0] is False
    assert check(tmp_path,now=NOW-timedelta(seconds=6))[0] is False
    raw=snapshot();raw['finished_utc']+=61
    assert check(tmp_path,raw)[0] is False

def test_source_clock_dst_and_currency_mismatch_fail_closed(tmp_path):
    raw=snapshot();raw['server']='another-terminal'
    assert check(tmp_path,raw)[2]=='MT5_CALENDAR_SERVER_MISMATCH'
    raw=snapshot();raw['server_time']+=3600
    assert check(tmp_path,raw)[2]=='MT5_CALENDAR_CLOCK_MISMATCH'
    assert check(tmp_path,currencies={'NZD','USD'})[2]=='MT5_CALENDAR_CURRENCY_NOT_COVERED'

def test_tentative_events_block_entire_server_day(tmp_path):
    raw=snapshot();event=raw['events'][0]
    event['exact_time']=False;event['time_server']=int(raw['server_time']/86400)*86400
    assert check(tmp_path,raw)[1]

def test_all_metadata_validated_even_after_a_matching_blackout(tmp_path):
    raw=snapshot();raw['events'].append({'time_server':'malformed'})
    assert check(tmp_path,raw)==(False,True,'NEWS_CALENDAR_INVALID')

def test_internal_filter_applies_even_when_trial_has_no_firm_news_restriction(tmp_path):
    p=tmp_path/'calendar.json';p.write_text(json.dumps(snapshot()))
    firm=load_firm_profiles()['ftmo_free_trial_50k_2step']
    assert not firm.news.enabled
    settings=Settings(_env_file=None,news_filter_enabled=True,news_calendar_path=p)
    assert configured_news(settings,firm,NOW,{'USD'})[1]
    p.unlink()
    assert configured_news(settings,firm,NOW,{'USD'})==(False,True,'NEWS_CALENDAR_INVALID')

def test_legacy_calendar_compatibility_and_native_requirement(tmp_path):
    p=tmp_path/'legacy.json';p.write_text(json.dumps({'source':'fixture',
        'valid_from':(NOW-timedelta(hours=1)).isoformat(),'valid_until':(NOW+timedelta(hours=1)).isoformat(),
        'events':[{'time':NOW.isoformat(),'impact':'high','currencies':['USD']}]}))
    assert news_state(p,NOW,{'USD'},2,2)==(True,True,'NEWS_BLACKOUT')
    assert news_state(p,NOW,{'USD'},2,2,require_native=True)[0] is False

def test_news_status_endpoint_requires_auth_and_reports_missing_source(client):
    r=client.get('/api/system/news');assert r.status_code==200
    assert r.json()['entry_filter_only'] and not r.json()['funded_ftmo_compliance_verified']
    assert client.get('/api/system/news',headers={'Authorization':'Bearer wrong'}).status_code==401


def test_ftmo_rule_binding_rejects_unreviewed_account_switch(factory):
    from qros.services.account_rules import account_rule_errors,identity
    from qros.db.models import SystemState
    from qros.db.session import session_scope
    from types import SimpleNamespace
    firm=SimpleNamespace(id='trial')
    with session_scope(factory) as db:
        assert account_rule_errors(db,firm,'FTMO-Demo','one')==['FTMO_ACCOUNT_RULE_BINDING_MISSING']
        db.add(SystemState(key='firm_account_binding:trial',data={'account_identity':identity('FTMO-Demo','one')}))
        db.flush()
        assert account_rule_errors(db,firm,'FTMO-Demo','one')==[]
        assert account_rule_errors(db,firm,'FTMO-Demo','two')==['FTMO_ACCOUNT_CHANGED_REVIEW_FUNDED_RULES']
        assert account_rule_errors(db,firm,'isolated-fixture','one')==[]
