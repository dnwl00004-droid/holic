from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock
import requests
from .history_v10 import FRED_SERIES, _fred_full_rows, transform_history
from ..reliability import store_history, now

ADDITIONAL = {
    "PPIFIS": ("PPI Final Demand YoY", "inflation", "%", "yoy"),
    "PCEPI": ("PCE YoY", "inflation", "%", "yoy"),
    "PCEPILFE": ("Core PCE YoY", "inflation", "%", "yoy"),
    "PPIFES": ("Core PPI YoY", "inflation", "%", "yoy"),
    "CCSA": ("Continuing Jobless Claims", "labor", "claims", "level"),
    "DGORDER": ("Durable Goods Orders YoY", "growth", "%", "yoy"),
    "DEXUSEU": ("USD per EUR", "fx", "USD/EUR", "level"),
    "DEXJPUS": ("JPY per USD", "fx", "JPY/USD", "level"),
    "DEXCHUS": ("CNY per USD (onshore)", "fx", "CNY/USD", "level"),
    "DEXUSUK": ("USD per GBP", "fx", "USD/GBP", "level"),
    "DEXCAUS": ("CAD per USD", "fx", "CAD/USD", "level"),
    "DTWEXBGS": ("Broad Trade-Weighted Dollar Index", "fx", "index", "level"),
    "VIXCLS": ("CBOE VIX Daily Close", "market", "index", "level"),
    "WCSSTUS1": ("Strategic Petroleum Reserve", "eia", "thousand bbl", "level"),
    "WCESTUS1": ("Crude Inventory ex-SPR", "eia", "thousand bbl", "level"),
    "WGTSTUS1": ("Gasoline Inventory", "eia", "thousand bbl", "level"),
    "WDISTUS1": ("Distillate Inventory", "eia", "thousand bbl", "level"),
    "WCRFPUS2": ("US Crude Production", "eia", "thousand bbl/day", "level"),
    "WPULEUS3": ("Refinery Utilization", "eia", "%", "level"),
    "WCRIMUS2": ("US Crude Imports", "eia", "thousand bbl/day", "level"),
    "WCREXUS2": ("US Crude Exports", "eia", "thousand bbl/day", "level"),
}
REGISTRY = {**{k:v for k,v in FRED_SERIES.items() if k!="WPSFD4"}, **{k: dict(zip(("label", "category", "unit", "transform"), v)) for k, v in ADDITIONAL.items() if k not in {"WCSSTUS1","WCESTUS1","WGTSTUS1","WDISTUS1","WCRFPUS2","WPULEUS3","WCRIMUS2","WCREXUS2"}}}

def build_official_history(root, workers=4, selected=None):
    root = Path(root); registry = {k: v for k, v in REGISTRY.items() if not selected or k in selected}
    circuit = Event(); failures_lock = Lock(); transport_failures = 0
    def fetch(item):
        nonlocal transport_failures
        sid, meta = item; path = root / "fred" / (sid + ".json")
        skipped = circuit.is_set()
        try:
            if skipped:
                raise RuntimeError("provider_circuit_open_after_transport_failures")
            raw = _fred_full_rows(sid)
            with failures_lock: transport_failures = 0
            hist = transform_history(raw, meta["transform"])
            d = store_history(path, {"id": sid, "kind": "fred", "source": "FRED", "source_url": "https://fred.stlouisfed.org/series/" + sid,
                                    "meta": meta, "history": hist, "raw_observation_count": len(raw), "vintage": "revised", "method": meta["transform"]})
        except Exception as e:
            # Avoid logging request headers or credentials.
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (401, 403, 429): circuit.set()
            if isinstance(e, (requests.Timeout, requests.ConnectionError)) or status in (500, 502, 503, 504):
                with failures_lock:
                    transport_failures += 1
                    if transport_failures >= 4: circuit.set()
            elif not skipped:
                with failures_lock: transport_failures = 0
            error = "provider_circuit_open_after_transport_failures" if skipped else type(e).__name__ + (":" + str(status) if status else "")
            d = store_history(path, None, error)
        h = d["history"]
        return {"id": sid, "kind": "fred", **meta, "path": "history/fred/" + sid + ".json" if h else None,
                "start": h[0]["date"] if h else None, "end": h[-1]["date"] if h else None, "count": len(h), "source": "FRED",
                "status": d["status"], "last_attempt": d.get("last_attempt"), "last_success": d.get("last_success"), "error": d.get("error"),
                "refresh_frequency": "daily collection; source frequency varies", "method": meta["transform"]}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fetch, registry.items()))
