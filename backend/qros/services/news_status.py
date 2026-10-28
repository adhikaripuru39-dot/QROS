"""Calendar observability, without connecting to MT5 from the API."""
import json
from datetime import datetime,timezone,timedelta
from qros.risk.news import configured_news,news_state
from qros.services import settings_store as st
from qros.db.models import ServiceHeartbeat

def news_status(db,settings,now=None):
    now=now or datetime.now(timezone.utc)
    firm=st.active_firm(db);hb=db.get(ServiceHeartbeat,'executor')
    detail=hb.broker_detail if hb else {}
    identity={'expected_server':None if detail.get('paper') else detail.get('server'),
              'expected_offset':detail.get('observed_server_utc_offset_seconds')}
    currencies={c for i in st.instruments(db) if i.enabled for c in (i.base,i.quote)}
    valid,_,reason=configured_news(settings,firm,now,currencies,**identity)
    enabled=settings.news_filter_enabled or firm.news.enabled
    flatten_news=bool(getattr(firm.news,'flatten_before_news',False))
    cancel_pending_news=bool(getattr(firm.news,'cancel_pending_before_news',False))
    entry_only=not (flatten_news or cancel_pending_news)
    result={'enabled':enabled,'source':'MT5 built-in economic calendar','coverage_valid':valid if enabled else False,
        'reason':reason,'observed_at':now.isoformat(),'entry_filter_only':entry_only,
        'flatten_before_news':flatten_news,'cancel_pending_before_news':cancel_pending_news,
        'funded_ftmo_compliance_verified':False,'max_age_seconds':settings.news_max_age_seconds,
        'minutes_before':max(settings.news_minutes_before if settings.news_filter_enabled else 0,firm.news.minutes_before),
        'minutes_after':max(settings.news_minutes_after if settings.news_filter_enabled else 0,firm.news.minutes_after),
        'minimum_importance':settings.news_min_importance,'symbols':[],'upcoming':[],
        'limitation':('Blocks new entries only. Does not prevent SL/TP/pending fills or force positions flat before restricted events.'
                      if entry_only else
                      'Blocks new entries and flattens managed positions / cancels pending orders during restricted news windows.')}
    for instrument in st.instruments(db):
        ok,blocked,why=configured_news(settings,firm,now,{instrument.base,instrument.quote},**identity)
        result['symbols'].append({'symbol':instrument.symbol,'coverage_valid':ok,'entry_blocked':blocked if enabled else False,'reason':why})
    try:
        raw=json.loads(settings.news_calendar_path.read_text(encoding='utf-8-sig'))
        if raw.get('source')!='mt5_builtin_calendar':return result
        result['last_export_utc']=datetime.fromtimestamp(raw['generated_utc'],timezone.utc).isoformat()
        result['source_server']=raw.get('server');result['source_complete']=raw.get('complete')
        result['event_count']=len(raw['events'])
        if not valid:return result
        offset=raw['server_time']-raw['generated_utc']
        for event in sorted(raw['events'],key=lambda e:e['time_server']):
            estimate=datetime.fromtimestamp(event['time_server']-offset,timezone.utc)
            if now-timedelta(minutes=result['minutes_after'])<=estimate<=now+timedelta(days=2) and event['importance']>=settings.news_min_importance:
                result['upcoming'].append({'name':event.get('name'),'currency':event['currency'],
                    'importance':event['importance'],'time_server':event['time_server'],
                    'display_utc_estimate':estimate.isoformat(),'exact_time':event['exact_time']})
        result['upcoming']=result['upcoming'][:100]
        result['time_note']='Blackouts use the current server axis. Future UTC display estimates do not certify DST mappings.'
    except (OSError,ValueError,KeyError,TypeError,AttributeError,OverflowError):pass
    return result
