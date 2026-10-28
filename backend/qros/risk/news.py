"""News checks fail closed. Native MT5 events stay on the trade-server axis.

UTC is used for snapshot freshness, not to certify future server/DST mappings.
"""
import json, math
from datetime import datetime,timezone,timedelta
from pathlib import Path


def _number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Invalid numeric calendar field')
    return value


def _native(raw,now,currencies,before,after,expected_server,expected_offset,min_importance,max_age):
    if raw.get('schema')!=2 or raw.get('complete') is not True or raw.get('read_only') is not True or raw.get('errors')!=0:
        return False,True,'MT5_CALENDAR_INCOMPLETE'
    generated=_number(raw['generated_utc']);finished=_number(raw['finished_utc'])
    age=now.timestamp()-generated
    if not -5<=age<=max_age or not 0<=finished-generated<=60:
        return False,True,'MT5_CALENDAR_STALE_OR_CLOCK_INVALID'
    server=_number(raw['server_time']);offset=round((server-generated)/60)*60
    if abs(server-generated-offset)>5 or not -43200<=offset<=50400 or offset%900:
        return False,True,'MT5_CALENDAR_OFFSET_INVALID'
    if expected_server is not None and raw.get('server')!=expected_server:
        return False,True,'MT5_CALENDAR_SERVER_MISMATCH'
    if expected_offset is not None and offset!=expected_offset:
        return False,True,'MT5_CALENDAR_CLOCK_MISMATCH'
    if not isinstance(raw.get('server'),str) or not raw['server']:
        raise ValueError('Source server required')
    coverage=raw['currencies']
    if not isinstance(coverage,list) or any(not isinstance(c,str) or len(c)!=3 or not c.isalpha() or c!=c.upper() for c in coverage):
        raise ValueError('Currency coverage malformed')
    required=(currencies-{'XAU','XAG'})|({'USD'} if currencies&{'XAU','XAG'} else set())
    if not required.issubset(set(coverage)):
        return False,True,'MT5_CALENDAR_CURRENCY_NOT_COVERED'
    server_now=server+age
    start=_number(raw['query_from_server']);end=_number(raw['query_until_server'])
    if not start<=server_now-after*60 or not server_now+before*60<end:
        return False,True,'MT5_CALENDAR_QUERY_COVERAGE_INVALID'
    events=raw['events'];blackout=False
    if not isinstance(events,list) or len(events)>10000:raise ValueError('Invalid event array')
    for event in events:
        when=_number(event['time_server']);importance=event['importance']
        if not start<=when<end or type(importance) is not int or not 0<=importance<=3:
            raise ValueError('Invalid native event')
        currency=event['currency']
        if currency not in coverage or type(event['exact_time']) is not bool:
            raise ValueError('Unresolved event metadata')
        if importance<min_importance or currency not in required:continue
        if event['exact_time']:
            blackout |= when-before*60<=server_now<=when+after*60
        else:
            day=math.floor(when/86400)*86400
            blackout |= day-before*60<=server_now<=day+86400+after*60
    return True,bool(blackout),'NEWS_BLACKOUT' if blackout else 'OK'


def news_state(path,now,currencies,before,after,*,expected_server=None,expected_offset=None,
               min_importance=2,max_age=120,require_native=False):
    if path is None:return False,True,'NEWS_CALENDAR_UNAVAILABLE'
    try:
        if now.tzinfo is None or not 0<=before<=240 or not 0<=after<=240:
            raise ValueError('Aware clock and bounded windows required')
        path=Path(path)
        if path.stat().st_size>10_000_000:raise ValueError('Calendar too large')
        raw=json.loads(path.read_text(encoding='utf-8-sig'))
        if raw.get('source')=='mt5_builtin_calendar':
            return _native(raw,now,set(currencies),before,after,expected_server,expected_offset,min_importance,max_age)
        if require_native:return False,True,'MT5_CALENDAR_SOURCE_REQUIRED'
        start=datetime.fromisoformat(raw['valid_from']);end=datetime.fromisoformat(raw['valid_until'])
        if not raw.get('source') or start.tzinfo is None or end.tzinfo is None or not start<=now<end:
            return False,True,'NEWS_CALENDAR_COVERAGE_INVALID'
        blackout=False
        if not isinstance(raw['events'],list):raise ValueError('Event array required')
        for event in raw['events']:
            when=datetime.fromisoformat(event['time'])
            if when.tzinfo is None or not isinstance(event['currencies'],list):raise ValueError('Invalid event')
            if event.get('impact')=='high' and currencies.intersection(event['currencies']):
                blackout |= when-timedelta(minutes=before)<=now<=when+timedelta(minutes=after)
        return True,bool(blackout),'NEWS_BLACKOUT' if blackout else 'OK'
    except (OSError,ValueError,KeyError,TypeError,AttributeError,OverflowError):
        return False,True,'NEWS_CALENDAR_INVALID'


def configured_news(settings,firm,now,currencies,**source_identity):
    enabled=settings.news_filter_enabled or firm.news.enabled
    if not enabled:return True,False,'NEWS_FILTER_DISABLED'
    before=max(firm.news.minutes_before,settings.news_minutes_before if settings.news_filter_enabled else 0)
    after=max(firm.news.minutes_after,settings.news_minutes_after if settings.news_filter_enabled else 0)
    return news_state(settings.news_calendar_path,now,currencies,before,after,
        min_importance=settings.news_min_importance,max_age=settings.news_max_age_seconds,
        require_native=settings.news_filter_enabled,**source_identity)
