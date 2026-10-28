from dataclasses import replace
import pytest
from qros.risk.drawdown import evaluate
from qros.risk.sizing import size_position
from qros.services.process_lock import ProcessLock

@pytest.mark.parametrize('value',[float('nan'),float('inf'),-float('inf')])
def test_drawdown_never_accepts_nonfinite(firm,limits,account,value):
    with pytest.raises(ValueError):evaluate(firm,limits,replace(account,equity=value))

@pytest.mark.parametrize('kwargs',[{'risk_amount':float('nan')},{'spread':-1},{'commission_per_lot':float('inf')}])
def test_sizing_rejects_invalid_costs(spec,kwargs):
    args={'risk_amount':100,'entry':1.1,'stop':1.09,**kwargs}
    assert size_position(spec,**args).rejected

def test_os_singleton_lock_releases(tmp_path):
    path=tmp_path/'service.lock'
    first=ProcessLock(path).acquire()
    with pytest.raises(RuntimeError):ProcessLock(path).acquire()
    first.release()
    ProcessLock(path).acquire().release()
