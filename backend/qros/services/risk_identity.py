"""Risk-day anchors belong to one account and firm, independent of UI mode."""
import hashlib

def risk_day_scope(firm_id,account,mode):
    venue='paper' if mode=='paper' else 'broker'
    identity=f'{firm_id}|{venue}|{account.server}|{account.login}'
    return 'risk:'+hashlib.sha256(identity.encode()).hexdigest()[:59]
