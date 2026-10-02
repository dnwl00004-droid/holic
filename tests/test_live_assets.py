import copy
import pandas as pd
from src.providers.assets_live import collect_assets, summarize
from src.reliability import atomic_json,read_json,blank_snapshot,validate_snapshot


def test_asset_outage_keeps_full_history_and_last_success(tmp_path):
    def fetch(*a,**k):
        return {"GC=F":pd.DataFrame({"close":[2000.0,2010.0]},index=pd.to_datetime(["2025-01-02","2025-01-03"]))}
    first,_,_=collect_assets(tmp_path,fetch)
    gold=next(x for x in first if x["id"]=="GC=F")
    def fail(*a,**k):raise TimeoutError()
    second,commodities,_=collect_assets(tmp_path,fail)
    cached=next(x for x in second if x["id"]=="GC=F")
    assert cached["count"]==2 and cached["status"]=="stale"
    assert cached["last_success"]==gold["last_success"]
    assert commodities["contracts"]["GC=F"]["value"]==2010
    assert commodities["contracts"]["SI=F"]["value"] is None


def test_asset_truncation_is_rejected(tmp_path):
    def fetch(*a,**k):return {"SPY":pd.DataFrame({"close":[100,101]},index=pd.to_datetime(["2024-01-02","2025-01-03"]))}
    collect_assets(tmp_path,fetch)
    def truncated(*a,**k):return {"SPY":pd.DataFrame({"close":[999]},index=pd.to_datetime(["2025-01-03"]))}
    _,_,market=collect_assets(tmp_path,truncated)
    assert market["SPY"]["status"]=="stale" and market["SPY"]["value"]==101


def test_insufficient_lookback_is_missing_not_shorter_window():
    out=summarize([{"date":"2025-01-01","value":100},{"date":"2025-01-02","value":110}])
    assert out["return_1d_pct"]==10
    assert out["return_6m_pct"] is None and out["ma50"] is None
    assert out["high_52w"] is None and out["volatility20_ann_pct"] is None


def test_mixed_dates_do_not_create_intermarket_ratio(tmp_path):
    def fetch(*a,**k):
        return {"GC=F":pd.DataFrame({"close":[2000]},index=pd.to_datetime(["2025-01-02"])),
                "SI=F":pd.DataFrame({"close":[20]},index=pd.to_datetime(["2025-01-03"]))}
    _,commodities,_=collect_assets(tmp_path,fetch)
    assert commodities["derived"]["gold_silver_ratio"]["value"] is None


def test_boolean_is_not_a_stock_price():
    snap=blank_snapshot();snap["tickers"]=[{"ticker":"TEST","price":{"close":True}}]
    import pytest
    with pytest.raises(ValueError):validate_snapshot(snap)


def test_full_derived_history_survives_source_outage(tmp_path):
    dates=pd.date_range("2024-01-01",periods=300,freq="D")
    def fetch(*a,**k):
        return {"GC=F":pd.DataFrame({"close":[2000+i for i in range(300)]},index=dates),
                "SI=F":pd.DataFrame({"close":[20+i/100 for i in range(300)]},index=dates)}
    items,_,_=collect_assets(tmp_path,fetch)
    ratio=next(x for x in items if x["id"]=="GOLD_SILVER_RATIO")
    assert ratio["count"]==300 and ratio["status"]=="ok"
    rows=read_json(tmp_path/"commodities/GOLD_SILVER_RATIO.json")["history"]
    import pytest
    assert rows[0]["value"]==100 and rows[-1]["value"]==pytest.approx(2299/22.99)
    def outage(*a,**k):raise TimeoutError()
    second,summary,_=collect_assets(tmp_path,outage)
    cached=next(x for x in second if x["id"]=="GOLD_SILVER_RATIO")
    assert cached["status"]=="stale" and cached["count"]==300
    assert read_json(tmp_path/"commodities/GOLD_SILVER_RATIO.json")["history"]==rows
    assert summary["derived"]["gold_silver_ratio"]["status"]=="stale"
