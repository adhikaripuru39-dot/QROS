"""FTMO programme rules are bound to the reviewed account, not its demo flag."""
import hashlib
from qros.db.models import SystemState

def identity(server,login):
    return hashlib.sha256(f'{server}|{login}'.encode()).hexdigest()

def account_rule_errors(db,firm,server,login):
    if not str(server or '').upper().startswith('FTMO'):return []
    row=db.get(SystemState,'firm_account_binding:'+firm.id)
    if row is None:return ['FTMO_ACCOUNT_RULE_BINDING_MISSING']
    if row.data.get('account_identity')!=identity(server,login):
        return ['FTMO_ACCOUNT_CHANGED_REVIEW_FUNDED_RULES']
    return []
