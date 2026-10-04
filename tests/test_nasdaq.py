import copy
import math
from datetime import datetime, timezone

import pandas as pd
import pytest
import requests

from src.providers import nasdaq, prices
from src.reliability import atomic_json, now


def quotes(symbol="SPY"):
    return {"status":{"rCode":200},"data":{"symbol":symbol,"totalRecords":2,"tradesTable":{"rows":[
        {"date":"01/03/2025","open":"$100.00","high":"$103.00","low":"$99.00","close":"$102.00","volume":"1,000"},
        {"date":"01/02/2025","open":"$99.00","high":"$101.00","low":"$98.00","close":"$100.00","volume":"900"},
    ]}}}


def test_quote_identity_pagination_and_ohlc_are_verified():
    frame=nasdaq.parse_quotes(quotes(),"SPY")
    assert frame.index.is_monotonic_increasing and frame["close"].iloc[-1]==102
    assert frame["volume"].iloc[-1]==1000
    with pytest.raises(nasdaq.QuoteError,match="symbol_mismatch"):
        nasdaq.parse_quotes(quotes("TLT"),"SPY")
    missing=quotes();missing["data"]["totalRecords"]=3
    with pytest.raises(nasdaq.QuoteError,match="incomplete_history_page"):
        nasdaq.parse_quotes(missing,"SPY")
    bad=quotes();bad["data"]["tradesTable"]["rows"][0]["high"]="$101"
    with pytest.raises(nasdaq.QuoteError,match="inconsistent_ohlc"):
        nasdaq.parse_quotes(bad,"SPY")


def test_missing_volume_is_missing_not_invented_zero():
    payload=quotes();payload["data"]["tradesTable"]["rows"][0]["volume"]="N/A"
    frame=nasdaq.parse_quotes(payload,"SPY")
    assert math.isnan(frame["volume"].iloc[-1])
    assert frame["close"].iloc[-1]==102 and frame.attrs["missing_volume_sessions"]==1


def test_duplicate_and_unadjusted_discontinuity_are_rejected():
    payload=quotes();rows=payload["data"]["tradesTable"]["rows"]
    rows[0]["date"]=rows[1]["date"]
    with pytest.raises(nasdaq.QuoteError,match="duplicate_session"):
        nasdaq.parse_quotes(payload,"SPY")
    payload=quotes();row=payload["data"]["tradesTable"]["rows"][0]
    row.update(open="$300",high="$302",low="$299",close="$300")
    with pytest.raises(nasdaq.QuoteError,match="discontinuity"):
        nasdaq.parse_quotes(payload,"SPY")


def test_provider_failure_keeps_verified_prices_and_success_time(tmp_path):
    attempted="2025-01-04T00:00:00+00:00"
    atomic_json(tmp_path/"SPY.json",{"source":nasdaq.SOURCE,"symbol":"SPY","payload":quotes(),"fetched_at":attempted,"requested_start":"2020-01-01","method":nasdaq.METHOD})
    class Failed:
        def get(self,*a,**k):raise requests.ReadTimeout()
    frame=nasdaq.fetch_daily("SPY",cache_dir=tmp_path,session=Failed())
    assert frame.attrs["status"]=="stale" and frame.attrs["fetched_at"]==attempted
    assert frame["close"].iloc[-1]==102 and frame.attrs["error"]=="ReadTimeout"


def test_rate_limit_stops_provider_and_retains_other_adapters(monkeypatch):
    def unavailable(*a,**k):
        class YFRateLimitError(Exception):pass
        raise YFRateLimitError()
    monkeypatch.setattr(prices,"nasdaq_daily",lambda *a,**k:{"SPY":pd.DataFrame({"close":[100]})})
    monkeypatch.setattr(prices,"yahoo_daily",unavailable)
    result=prices.download_daily(["SPY","CL=F"])
    assert "SPY" in result and "CL=F" not in result
    assert result.errors["CL=F"]=="rate_limited_429"

def test_new_sector_and_broad_market_funds_use_nasdaq_etf_endpoint(tmp_path):
    from src.providers.history_v10 import MARKET_TICKERS
    symbols={ticker for ticker,meta in MARKET_TICKERS.items() if meta["category"]=="Sector ETF"}
    assert len(symbols)==11 and symbols|{"QQQ","IWM"} <= nasdaq.ETF_SYMBOLS
    class Session:
        def get(self,url,**kwargs):
            assert kwargs["params"]["assetclass"]=="etf"
            response=requests.Response()
            response.status_code=200
            response._content=__import__("json").dumps(quotes("XLK")).encode()
            return response
    frame=nasdaq.fetch_daily("XLK",cache_dir=tmp_path,session=Session())
    assert frame["close"].iloc[-1]==102
    assert "/etf/xlk/" in frame.attrs["source_url"]


def test_fred_timeout_retry_does_not_retry_rate_limit():
    from src.providers.history_v10 import _fred_full_rows
    class Session:
        calls=0
        def get(self,*a,**k):
            self.calls+=1
            if self.calls==1:raise requests.ReadTimeout()
            r=requests.Response();r.status_code=200;r._content=b"observation_date,DGS10\n2025-01-02,4.3\n";return r
    session=Session();assert _fred_full_rows("DGS10",session)[0]["value"]==4.3
    assert session.calls==2
    class Limited:
        calls=0
        def get(self,*a,**k):
            self.calls+=1
            r=requests.Response();r.status_code=429;return r
    session=Limited()
    with pytest.raises(requests.HTTPError):_fred_full_rows("DGS10",session)
    assert session.calls==1
