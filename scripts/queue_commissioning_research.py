from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()/'backend'))
from qros.config.settings import Settings
from qros.db.session import session_factory,session_scope
from qros.db.models import BackgroundJob,ServiceHeartbeat,SystemState,ControlState
from qros.services.readiness import readiness
from sqlalchemy import select
s=Settings();factory=session_factory(s.database_url)
with session_scope(factory) as db:
    report=readiness(db,s)
    market=db.get(SystemState,'market_observations')
    print(json.dumps({'readiness':report,'market':market.data if market else None},indent=2,default=str))
    for symbol in ['XAUUSD','EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD']:
        jid='commissioning-'+symbol+'-M15'
        if db.get(BackgroundJob,jid) is None:db.add(BackgroundJob(id=jid,kind='research',status='queued',payload={'symbol':symbol,'timeframe':'M15','days':180,'finalize_oos':False},result={}))
print('Queued seven read-only research jobs using the captured real historical archives.')
