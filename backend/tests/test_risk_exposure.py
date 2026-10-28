from qros.risk.exposure import ExposureLeg,currency_exposure,max_directional_risk

def test_shared_usd_direction_adds():
    legs=[ExposureLeg('EURUSD','EUR','USD','buy',100),ExposureLeg('GBPUSD','GBP','USD','buy',150)]
    exp=currency_exposure(legs)
    assert exp['EUR']['long']==100
    assert exp['USD']['short']==250
    assert max_directional_risk(legs)==('USD',250)

def test_no_netting_credit():
    exp=currency_exposure([ExposureLeg('EURUSD','EUR','USD','buy',100),ExposureLeg('EURUSD','EUR','USD','sell',75)])
    assert exp['EUR']['max_directional']==100
    assert exp['USD']['max_directional']==100

def test_empty():assert max_directional_risk([])==(None,0)
