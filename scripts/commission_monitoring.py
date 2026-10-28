"""Commission read-only MT5 monitoring and capture account funding provenance."""
from pathlib import Path
import sys,json,time
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from qros.broker.mt5_adapter import MT5Adapter
adapter=MT5Adapter(path=r'C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe',allow_orders=False)
try:
    status=adapter.connect()
    if not status.connected:raise RuntimeError(status.error)
    symbols=['XAUUSD','EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD']
    for _ in range(8):
        for symbol in symbols:adapter.quote(symbol)
        time.sleep(.5)
    account=adapter.account_info()
    history=adapter._mt5.history_deals_get(datetime(2000,1,1,tzinfo=timezone.utc),datetime.now(timezone.utc)+timedelta(days=1))
    funding=[d for d in history or () if int(d.type)==2 and float(d.profit)>0]
    initial=min(funding,key=lambda d:d.time) if funding else None
    report={'observed_at':datetime.now(timezone.utc).isoformat(),'connected':True,'is_demo':account.is_demo,'server':account.server,'currency':account.currency,'balance':account.balance,'equity':account.equity,'initial_capital_observed':float(initial.profit) if initial else None,'funding_deal_time_raw':int(initial.time) if initial else None,'clock_verified_current':adapter.clock_verified,'observed_utc_offset_seconds':adapter._utc_offset_seconds,'terminal_trade_allowed':adapter.ping().detail.get('terminal_trade_allowed'),'orders_submitted':0,'quotes':{symbol:vars(adapter.quote(symbol)) for symbol in symbols}}
    path=Path('var/readiness/commissioning.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='quotes'},indent=2))
finally:adapter.disconnect()
