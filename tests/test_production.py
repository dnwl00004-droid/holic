import copy, json
import pandas as pd
from src.reliability import atomic_json,store_history,read_json,validate_snapshot,blank_snapshot
from src.analytics.macro_v8 import macro_scores,sector_macro_fit
from src.analytics.fundamentals_plus import quality_snapshot
from src.analytics.signal_backtest_v7 import _forward,score_events,aggregate_signal_results
from src.providers.calendar_live import parse_fomc,parse_bls,event
from src.providers.eia_live import parse_history
from datetime import date

def test_failed_refresh_retains_last_good_series(tmp_path):
    p=tmp_path/'series.json';d={'source':'FRED','history':[{'date':'2024-01-01','value':3},{'date':'2024-02-01','value':4}]}
    first=store_history(p,d);second=store_history(p,{'source':'FRED','history':[]})
    assert second['history']==first['history'] and second['status']=='stale'
    assert second['last_success']==first['last_success']

def test_demo_cannot_be_used_as_fallback(tmp_path):
    p=tmp_path/'demo.json';atomic_json(p,{'source':'DEMO','history':[{'date':'2024-01-01','value':5}]})
    assert store_history(p,None)['status']=='unavailable'

def test_truncated_or_nonfinite_history_does_not_replace(tmp_path):
    p=tmp_path/'series.json';good={'source':'FRED','history':[{'date':'2023-01-01','value':1},{'date':'2024-01-01','value':2}]};store_history(p,good)
    assert store_history(p,{'source':'FRED','history':[{'date':'2024-01-01','value':3}]})['history']==good['history']
    assert store_history(p,{'source':'FRED','history':[{'date':'2024-01-01','value':float('nan')}]})['status']=='stale'

def test_atomic_json_leaves_original_on_validation_failure(tmp_path):
    p=tmp_path/'a.json';atomic_json(p,{'a':3})
    try:atomic_json(p,{'a':float('nan')})
    except ValueError:pass
    assert read_json(p)=={'a':3}

def test_missing_macro_not_neutral():
    result=macro_scores({})
    assert result['regime']=='Unavailable' and result['macro_risk_score'] is None
    assert all(v is None for v in result['axes'].values())
    assert sector_macro_fit('Technology',result)['score'] is None

def test_liquidity_change_uses_billions():
    result=macro_scores({'WALCL':{'transform':'millions_to_bn','change_3m_raw':100000}})
    assert result['axes']['liquidity']==60

def test_missing_capex_is_not_zero_and_debt_not_double_counted():
    def node(rows):return {'units':{'USD':rows}}
    def instant(v):return {'val':v,'form':'10-K','end':'2025-12-31','filed':'2026-02-01'}
    f={'facts':{'us-gaap':{'NetCashProvidedByUsedInOperatingActivities':node([{'frame':'CY2025','val':100}]),
        'LongTermDebtAndFinanceLeaseObligationsCurrent':node([instant(10)]),'LongTermDebtCurrent':node([instant(10)]),'LongTermDebtNoncurrent':node([instant(90)]),'LongTermDebt':node([instant(100)])}}}
    out=quality_snapshot(f);assert out['base']['fcf'] is None;assert out['base']['debt']==100;assert out['base']['net_debt'] is None

def test_backtest_uses_next_open_and_peak_drawdown():
    df=pd.DataFrame({'open':[100,110,120,120],'close':[100,120,130,117]})
    result=_forward(df,0,3)
    assert round(result['return_pct'],5)==round((117/110-1)*100,5)
    assert round(result['max_drawdown_pct'],5)==-10

def test_aggregation_uses_all_events_not_last_twelve():
    rows=[{'date':f'2025-01-{i:02d}','ret_20d_pct':1,'max_20d_pct':2,'dd_20d_pct':-1} for i in range(1,21)]
    one=score_events(rows);assert len(one['events'])==12
    out=aggregate_signal_results({'TEST':{'RS_BEFORE_PRICE':one}})
    assert out['RS_BEFORE_PRICE']['count']==20

def test_fomc_year_blocks_do_not_bleed():
    text='''<div class="panel"><div class="panel-heading">2026 FOMC Meetings</div><div class="row fomc-meeting"><div class="fomc-meeting__month">October</div><div class="fomc-meeting__date">27-28</div></div></div><div class="panel"><div class="panel-heading">2027 FOMC Meetings</div><div class="row fomc-meeting"><div class="fomc-meeting__month">March</div><div class="fomc-meeting__date">16-17</div></div></div>'''
    assert {e['date'] for e in parse_fomc(text)}=={'2026-10-28','2027-03-17'}

def test_ics_and_dst_conversion():
    e=parse_bls('BEGIN:VEVENT\nDTSTART;TZID=US-Eastern:20261002T083000\nSUMMARY:Employment Situation\nEND:VEVENT')[0]
    assert e['datetime_kst'].startswith('2026-10-02T21:30')
    assert event(date(2026,12,4),'Employment Situation','BLS','08:30')['datetime_kst'].startswith('2026-12-04T22:30')

def test_eia_raw_table():
    text='<table><tr><td>2026-Sep</td><td>09/18</td><td>426,398</td><td>09/25</td><td>427,320</td></tr></table>'
    assert parse_history(text)[-1]=={'date':'2026-09-25','value':427320}


def test_missing_revision_and_catalyst_are_unavailable():
    from src.analytics.ranking_v7 import revision_score,catalyst_score
    assert revision_score({})['score'] is None
    assert catalyst_score({})['score'] is None


def test_eia_holiday_exception_uses_header_cell():
    from src.providers.calendar_live import parse_eia
    text='<p>Wednesday 10:30</p><table><tr><th>October 9, 2026</th><td>October 15, 2026</td><td>Thursday</td><td>12:00 p.m.</td><td>Columbus Day</td></tr></table>'
    rows=parse_eia(text)
    assert any(e['date']=='2026-10-15' and e['time_et']=='12:00 PM' for e in rows)
    assert not any(e['date']=='2026-10-14' for e in rows)
