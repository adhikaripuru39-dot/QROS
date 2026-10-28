from qros.audit.log import record,verify_chain
from qros.db.session import session_scope

def test_chain_survives_reload(factory):
    with session_scope(factory) as db:
        record(db,'owner','one',{'b':2,'a':1});record(db,'owner','two')
    with session_scope(factory) as db:
        assert verify_chain(db)=={'ok':True,'checked':2,'broken_at_id':None}

def test_historical_tamper_detected(factory):
    with session_scope(factory) as db:
        first=record(db,'owner','one');record(db,'owner','two');first.data={'altered':True};db.flush()
        assert not verify_chain(db)['ok']

def test_middle_deletion_detected(factory):
    with session_scope(factory) as db:
        record(db,'owner','one');middle=record(db,'owner','two');record(db,'owner','three');db.delete(middle);db.flush()
        assert not verify_chain(db)['ok']

def test_concurrent_audit_writers_keep_one_chain(factory):
    from concurrent.futures import ThreadPoolExecutor
    def writer(worker):
        for index in range(8):
            with session_scope(factory) as db:record(db,str(worker),'concurrent',{'index':index})
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(writer,range(4)))
    with session_scope(factory) as db:
        result=verify_chain(db)
        assert result['ok'] and result['checked']==32
