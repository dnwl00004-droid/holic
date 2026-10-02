import requests

from src.providers import live_history
from src.reliability import store_history


def test_shared_endpoint_outage_stops_pending_requests_and_keeps_cache(tmp_path, monkeypatch):
    keys=list(live_history.REGISTRY)[:12]
    key=keys[-1]
    first=store_history(tmp_path/"fred"/(key+".json"),{"source":"FRED","history":[{"date":"2024-01-01","value":10.0}]})
    calls=[]
    def outage(series):
        calls.append(series)
        raise requests.ReadTimeout()
    monkeypatch.setattr(live_history,"_fred_full_rows",outage)
    items=live_history.build_official_history(tmp_path,workers=4,selected=keys)
    assert 4<=len(calls)<=7 and len(calls)<len(keys)
    assert len(items)==len(keys)
    cached=next(x for x in items if x["id"]==key)
    assert cached["status"]=="stale" and cached["count"]==1
    assert cached["last_success"]==first["last_success"]
    assert cached["error"]=="provider_circuit_open_after_transport_failures"


def test_success_resets_consecutive_outage_counter(tmp_path,monkeypatch):
    keys=list(live_history.REGISTRY)[:7];calls=[]
    def occasional_failure(series):
        calls.append(series)
        if series==keys[3]:return [{"date":"2024-01-01","value":3.0}]
        raise requests.ReadTimeout()
    monkeypatch.setattr(live_history,"_fred_full_rows",occasional_failure)
    items=live_history.build_official_history(tmp_path,workers=1,selected=keys)
    assert len(calls)==7
    assert next(x for x in items if x["id"]==keys[3])["status"]=="ok"


def test_missing_individual_series_does_not_stop_other_series(tmp_path,monkeypatch):
    keys=list(live_history.REGISTRY)[:6];calls=[]
    def missing_series(series):
        calls.append(series)
        response=requests.Response();response.status_code=404
        raise requests.HTTPError(response=response)
    monkeypatch.setattr(live_history,"_fred_full_rows",missing_series)
    items=live_history.build_official_history(tmp_path,workers=4,selected=keys)
    assert len(calls)==6 and all(x["error"]=="HTTPError:404" for x in items)


def test_rate_limit_stops_remaining_queued_requests(tmp_path,monkeypatch):
    keys=list(live_history.REGISTRY)[:12];calls=[]
    def rate_limited(series):
        calls.append(series)
        response=requests.Response();response.status_code=429
        raise requests.HTTPError(response=response)
    monkeypatch.setattr(live_history,"_fred_full_rows",rate_limited)
    items=live_history.build_official_history(tmp_path,workers=4,selected=keys)
    assert 1<=len(calls)<=4 and len(items)==12
    assert any(x["error"]=="HTTPError:429" for x in items)
