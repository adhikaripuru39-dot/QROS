"""Evidence attestation fixtures are isolated; no strategy is promoted."""
from copy import deepcopy
from qros.db.models import Strategy,EvidenceReport,Experiment
from qros.db.session import session_scope
from qros.services.evidence import canonical_hash,verify_report,strategy_eligibility,transition_evidence
from qros.research.runner import implementation_hash


def evidence_fixture(db):
    runtime={'strategy_id':'momentum','timeframe_seconds':900}
    cfg={'initial_cash':100000,'min_lot':.1}
    code=implementation_hash();config_hash=canonical_hash(cfg)
    content={'eligible':True,'selected_candidate':'momentum','oos':{'evaluated':True,'holdout_hash':'b'*64},'config':cfg,'binding':{'source_dataset_hash':'a'*64,'code_hash':code,'config_hash':config_hash},'runtime_spec_hash':canonical_hash(runtime)}
    strategy=Strategy(id='s1',hypothesis_id='momentum',family='momentum',name='fixture',status='PAPER_TRADING',spec={'runtime':runtime,'validation_report_id':'r1','validated_config_hash':config_hash})
    report=EvidenceReport(id='r1',strategy_id='s1',kind='validation',passed=True,dataset_hash='a'*64,code_hash=code,config_hash=config_hash,report_hash=canonical_hash(content),content=content)
    db.add_all([strategy,report]);db.flush()
    return strategy,report


def test_evidence_content_and_columns_must_agree(factory):
    with session_scope(factory) as db:
        strategy,report=evidence_fixture(db)
        assert verify_report(db,'r1','s1','validation')[1]==[]
        report.dataset_hash='c'*64
        assert 'EVIDENCE_CONTENT_BINDING_MISMATCH' in verify_report(db,'r1','s1','validation')[1]


def test_config_and_runtime_changes_invalidate_evidence(factory):
    with session_scope(factory) as db:
        strategy,report=evidence_fixture(db)
        assert strategy_eligibility(db,strategy,'paper')==[]
        strategy.spec={**strategy.spec,'runtime':{'timeframe_seconds':3600}}
        assert 'RUNTIME_SPEC_NOT_VALIDATED' in strategy_eligibility(db,strategy,'paper')
        changed=deepcopy(report.content);changed['config']['min_lot']=1.;report.content=changed;report.report_hash=canonical_hash(changed)
        assert 'EVIDENCE_CONFIG_HASH_MISMATCH' in verify_report(db,'r1','s1','validation')[1]


def test_oos_report_must_bind_actual_hypothesis_and_exact_report(factory):
    with session_scope(factory) as db:
        strategy,report=evidence_fixture(db)
        exp=Experiment(id='o1',hypothesis_id='different',kind='oos',status='completed',dataset_version=report.dataset_hash,code_version=report.code_hash,config={},results={'eligible':True})
        db.add(exp);db.flush()
        reasons=transition_evidence(db,strategy,'VALIDATED',{'validation_report_id':'r1','oos_experiment_id':'o1'})
        assert 'OOS_REPORT_BINDING_MISMATCH' in reasons


def test_demo_requires_bound_forward_report(factory):
    with session_scope(factory) as db:
        strategy,_=evidence_fixture(db)
        assert 'EVIDENCE_REPORT_NOT_FOUND' in strategy_eligibility(db,strategy,'demo')
