"""Evidence references are resolved and bound to immutable worker reports."""
import hashlib,json
from qros.db.models import EvidenceReport,Experiment,Strategy
from qros.research.runner import implementation_hash

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False,default=str).encode()).hexdigest()

def verify_report(db,report_id,strategy_id,kind=None):
    report=db.get(EvidenceReport,report_id)
    if report is None:return None,['EVIDENCE_REPORT_NOT_FOUND']
    errors=[]
    if report.strategy_id!=strategy_id:errors.append('EVIDENCE_STRATEGY_MISMATCH')
    if kind and report.kind!=kind:errors.append('EVIDENCE_KIND_MISMATCH')
    if not report.passed:errors.append('EVIDENCE_GATES_NOT_PASSED')
    if canonical_hash(report.content)!=report.report_hash:errors.append('EVIDENCE_HASH_MISMATCH')
    if report.code_hash!=implementation_hash():errors.append('EVIDENCE_CODE_CHANGED_REVALIDATE')
    if not all(isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value) for value in (report.dataset_hash,report.code_hash,report.config_hash)):
        errors.append('EVIDENCE_BINDING_INVALID')
    binding=report.content.get('binding',{})
    if binding.get('source_dataset_hash')!=report.dataset_hash or binding.get('code_hash')!=report.code_hash or binding.get('config_hash')!=report.config_hash:
        errors.append('EVIDENCE_CONTENT_BINDING_MISMATCH')
    if report.kind=='validation':
        if not report.content.get('eligible') or not report.content.get('oos',{}).get('evaluated') or not report.content.get('oos',{}).get('holdout_hash'):
            errors.append('COMPLETE_VALIDATION_REQUIRED')
        if canonical_hash(report.content.get('config',{}))!=report.config_hash:
            errors.append('EVIDENCE_CONFIG_HASH_MISMATCH')
        strategy=db.get(Strategy,strategy_id)
        if strategy and report.content.get('selected_candidate')!=strategy.hypothesis_id:
            errors.append('EVIDENCE_HYPOTHESIS_MISMATCH')
    return report,errors

def transition_evidence(db,strategy,target,evidence):
    errors=[]
    if target=='DEMO_TESTING':
        from qros.services.demo_testing import grant_errors
        if evidence.get('demo_test_grant')!='demo_test_grant:'+strategy.id:
            return ['DEMO_TEST_GRANT_REFERENCE_MISMATCH']
        return grant_errors(db,strategy,mode='demo')
    if target=='RESEARCH':
        from qros.research.registry import strategy_registry
        if strategy.hypothesis_id not in {x.id for x in strategy_registry()}:errors.append('UNKNOWN_REGISTERED_HYPOTHESIS')
        if evidence.get('hypothesis_id')!=strategy.hypothesis_id:errors.append('HYPOTHESIS_REFERENCE_MISMATCH')
    elif target=='BACKTESTED':
        exp=db.get(Experiment,evidence.get('experiment_id',''))
        if exp is None or exp.status!='completed' or exp.kind!='backtest':errors.append('COMPLETED_BACKTEST_REQUIRED')
        elif exp.hypothesis_id!=strategy.hypothesis_id or exp.dataset_version!=evidence.get('dataset_version'):errors.append('BACKTEST_REFERENCE_MISMATCH')
    elif target=='VALIDATED':
        report,problems=verify_report(db,evidence.get('validation_report_id',''),strategy.id,'validation');errors+=problems
        exp=db.get(Experiment,evidence.get('oos_experiment_id',''))
        if exp is None or exp.kind!='oos' or exp.status!='completed' or not exp.results or not exp.results.get('eligible'):errors.append('PASSED_UNTOUCHED_OOS_REQUIRED')
        elif report and (exp.hypothesis_id!=strategy.hypothesis_id or exp.dataset_version!=report.dataset_hash or exp.code_version!=report.code_hash or canonical_hash(exp.results)!=report.report_hash):errors.append('OOS_REPORT_BINDING_MISMATCH')
    elif target in ('PAPER_TRADING','DEMO_APPROVED','LIVE_APPROVED','ACTIVE'):
        report_id=strategy.spec.get('validation_report_id')
        _,problems=verify_report(db,report_id or '',strategy.id,'validation');errors+=problems
        if target in ('DEMO_APPROVED','LIVE_APPROVED'):
            key='paper_report_id' if target=='DEMO_APPROVED' else 'demo_report_id'
            kind='paper' if target=='DEMO_APPROVED' else 'demo'
            report,problems=verify_report(db,evidence.get(key,''),strategy.id,kind);errors+=problems
            if report and (report.content.get('n',0)<100 or not report.content.get('reconciliation_clean') or not report.content.get('min_forward_days_met')):errors.append('FORWARD_EVIDENCE_INSUFFICIENT')
    return errors

def strategy_eligibility(db,strategy,mode):
    if mode=='off':return ['TRADING_MODE_OFF']
    if strategy.status=='DEMO_TESTING':
        from qros.services.demo_testing import grant_errors
        return grant_errors(db,strategy,mode)
    report,errors=verify_report(db,strategy.spec.get('validation_report_id',''),strategy.id,'validation')
    if report:
        if not report.content.get('eligible') or not report.content.get('oos',{}).get('evaluated'):errors.append('COMPLETE_VALIDATION_REQUIRED')
        if report.content.get('runtime_spec_hash')!=canonical_hash(strategy.spec.get('runtime',{})):errors.append('RUNTIME_SPEC_NOT_VALIDATED')
        if strategy.spec.get('validated_config_hash')!=report.config_hash:errors.append('RUNTIME_CONFIG_NOT_VALIDATED')
    if mode in ('demo','live'):
        key='paper_report_id' if mode=='demo' else 'demo_report_id'
        forward,problems=verify_report(db,strategy.spec.get(key,''),strategy.id,'paper' if mode=='demo' else 'demo')
        errors+=problems
        if forward and (forward.content.get('n',0)<100 or not forward.content.get('reconciliation_clean') or not forward.content.get('min_forward_days_met')):errors.append('FORWARD_EVIDENCE_INSUFFICIENT')
    return errors
