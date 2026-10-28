from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()/'backend'))
from qros.config.settings import Settings
from qros.db.session import session_factory,session_scope
from qros.db.models import BackgroundJob,Experiment,OrderLedger,Trade
from qros.audit.log import verify_chain
from sqlalchemy import select,func
s=Settings()
with session_scope(session_factory(s.database_url)) as db:
    jobs=list(db.execute(select(BackgroundJob)).scalars())
    print(json.dumps({'jobs':[{'id':j.id,'status':j.status,'error':j.error,'candidates':len(j.result.get('candidates',[])),'eligible':j.result.get('eligible')} for j in jobs],'experiments':db.scalar(select(func.count(Experiment.id))),'orders':db.scalar(select(func.count(OrderLedger.client_order_id))),'trades':db.scalar(select(func.count(Trade.id))),'audit':verify_chain(db)},indent=2))
