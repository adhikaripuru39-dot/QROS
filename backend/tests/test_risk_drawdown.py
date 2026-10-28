from dataclasses import replace
import pytest
from qros.config.schemas import DrawdownType, DailyLossAnchor, AmountBasis
from qros.risk.drawdown import evaluate, daily_floor, total_floor

@pytest.mark.parametrize("mode,expected", [(DrawdownType.STATIC,90000),(DrawdownType.TRAILING_EOD,93000),(DrawdownType.TRAILING_INTRADAY,95000)])
def test_total_floor_modes(firm,account,mode,expected):
    firm.max_loss.drawdown_type=mode
    assert total_floor(firm,account)[2] == expected

@pytest.mark.parametrize("mode", [DrawdownType.TRAILING_EOD,DrawdownType.TRAILING_INTRADAY])
def test_trailing_locks_at_initial(firm,account,mode):
    firm.max_loss.drawdown_type=mode
    assert total_floor(firm,replace(account,hwm_equity=125000,hwm_eod_balance=125000))[2]==100000
    firm.max_loss.trail_lock_at_initial=False
    assert total_floor(firm,replace(account,hwm_equity=125000,hwm_eod_balance=125000))[2]==115000

def test_effective_floor_and_buffer(firm,limits,account):
    result=evaluate(firm,limits,account)
    assert result.daily_floor==95000
    assert result.effective_floor==98000
    assert result.remaining_to_effective_floor==2000
    assert not result.halt_required

def test_exact_stop_boundary_halts(firm,limits,account):
    result=evaluate(firm,limits,replace(account,equity=98000))
    assert result.internal_daily_stop and result.halt_required
    assert 'INTERNAL_DAILY_STOP' in result.halt_reasons
    assert result.remaining_to_effective_floor==0

def test_floating_profit_does_not_increase_internal_capacity(firm,limits,account):
    assert evaluate(firm,limits,replace(account,equity=101000)).internal_measured==100000
    assert evaluate(firm,limits,replace(account,equity=99000)).internal_measured==99000

def test_daily_anchor_and_basis(firm,account):
    firm.daily_loss.anchor=DailyLossAnchor.START_OF_DAY_EQUITY
    firm.daily_loss.amount_basis=AmountBasis.ANCHOR
    assert daily_floor(firm,replace(account,sod_equity=110000))==(110000,5500,104500)

def test_zero_initial_rejected(firm,limits,account):
    with pytest.raises(ValueError):evaluate(firm,limits,replace(account,initial_balance=0))
