from src.providers.calendar_v9 import _impact, _event
from datetime import date

def test_event_importance():
    assert _impact('FOMC Policy Decision') == 'HIGH'
    assert _impact('Consumer Price Index CPI') == 'HIGH'
    assert _impact('EIA Petroleum Status Report') == 'MEDIUM'

def test_event_shape():
    x=_event(date.today(),'FOMC Policy Decision','Federal Reserve','Central Bank','14:00')
    assert x['days_from_today']==0
    assert x['importance']=='HIGH'
