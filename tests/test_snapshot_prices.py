import json
import numpy as np
import pandas as pd

from src.analytics.patterns import vcp_proxy
from src.reliability import validate_snapshot


def bars(close):
    return pd.DataFrame({"close":close,"open":close,"high":close*1.005,"low":close*0.995,"volume":[1000.0]*len(close)},index=pd.bdate_range("2024-01-02",periods=len(close)))


def test_contracting_swings_use_high_peaks_and_low_troughs():
    values=np.interp(np.arange(130),[0,10,25,40,55,70,85,100,115,129],[90,100,70,105,84,108,97.2,107,102,106])
    result=vcp_proxy(bars(values))
    assert result["detected"] is True
    assert len(result["contractions"])==4
    assert all(a>b for a,b in zip(result["contractions"],result["contractions"][1:]))


def test_rsi_uses_wilder_seed_and_returns_a_scalar():
    from src.analytics.technicals_plus import rsi14
    prices=[44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,45.89,46.03,45.61,46.28,46.28]
    assert rsi14(pd.Series(prices))==70.46
    assert rsi14(pd.Series(range(1,21)))==100
    assert rsi14(pd.Series(range(20,0,-1)))==0
    assert rsi14(pd.Series([100.0]*20)) is None


def test_complete_snapshot_from_quotes_can_publish_and_align_dates(tmp_path,monkeypatch):
    import src.build_snapshot as builder
    universe=pd.DataFrame([{"ticker":"AAA","provider_ticker":"AAA","company":"A","sector":"Technology","industry":"Software"},
                           {"ticker":"BBB","provider_ticker":"BBB","company":"B","sector":"Industrials","industry":"Machinery"}])
    benchmark=bars(np.linspace(100,140,320));benchmark.attrs.update(source="test-only validated quote fixture",status="ok")
    stock=bars(np.linspace(80,130,321));stock.attrs.update(benchmark.attrs)
    frames={"SPY":benchmark,"AAA":stock,"BBB":stock.copy()}
    monkeypatch.setattr(builder,"load_sp500",lambda:universe)
    monkeypatch.setattr(builder,"download_daily",lambda symbols,**kwargs:{t:frames[t] for t in symbols})
    snapshot=builder.build(tmp_path/"latest.json",tmp_path/"signals.json")
    assert validate_snapshot(snapshot)
    assert snapshot["meta"]["price_coverage_pct"]==100
    assert all(r["price"]["as_of"]==snapshot["meta"]["as_of"] for r in snapshot["tickers"])
    encoded=json.dumps(snapshot,allow_nan=False)
    assert len(json.loads(encoded)["tickers"])==2
