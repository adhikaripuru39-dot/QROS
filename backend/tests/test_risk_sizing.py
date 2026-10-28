from dataclasses import replace
import pytest
from qros.risk.sizing import floor_to_step,loss_per_lot,size_position

@pytest.mark.parametrize('volume,step,expected',[(0.019,0.01,0.01),(0.29,0.01,0.29),(1.24,0.25,1.0)])
def test_floor(volume,step,expected):assert floor_to_step(volume,step)==expected

def test_costs_and_risk_budget(spec):
    base=size_position(spec,100,1.1,1.099)
    costly=size_position(spec,100,1.1,1.099,0.0002,5,7)
    assert costly.volume<base.volume
    assert costly.risk_at_volume<=100
    assert costly.loss_per_lot==pytest.approx(132)

def test_never_rounds_up_to_minimum(spec):
    result=size_position(spec,0.01,1.1,1.099)
    assert result.rejected and result.volume==0

@pytest.mark.parametrize('risk,entry,stop',[(0,1.1,1.099),(100,1.1,1.1),(100,0,1)])
def test_invalid_inputs(spec,risk,entry,stop):assert size_position(spec,risk,entry,stop).rejected

def test_stop_minimum_and_lot_cap(spec):
    assert size_position(replace(spec,min_stop_points=200),100,1.1,1.099).rejected
    assert size_position(spec,10000,1.1,1.099,max_lots_override=.25).volume==.25
