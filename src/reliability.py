"""Strict data contracts for static financial snapshots."""
from __future__ import annotations
import json, math, os, tempfile
from datetime import datetime, timezone, date
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat()

def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default

def is_demo(data):
    return bool((data or {}).get("meta", {}).get("demo")) or "demo" in str((data or {}).get("source", "")).lower()

def atomic_json(path, data):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    fd, temp = tempfile.mkstemp(prefix=p.name + ".", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        os.replace(temp, p)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def valid_history(rows):
    if not isinstance(rows, list) or not rows: return False
    last = ""
    for row in rows:
        try:
            dt = date.fromisoformat(row["date"])
            v = row["value"]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): return False
            if dt > datetime.now(timezone.utc).date() or row["date"] <= last: return False
            last = row["date"]
        except (KeyError, TypeError, ValueError): return False
    return True

def store_history(path, payload, error=None):
    """Keep the last verified full series when any replacement is invalid."""
    previous = read_json(path, {})
    attempted = now()
    if payload and not is_demo(payload) and valid_history(payload.get("history")):
        if valid_history(previous.get("history")) and not is_demo(previous):
            # Reject truncated downloads rather than silently discarding MAX history.
            if payload["history"][0]["date"] > previous["history"][0]["date"] or payload["history"][-1]["date"] < previous["history"][-1]["date"]:
                return store_history(path, None, "history_regression")
        payload.update(status="ok", fetched_at=attempted, last_attempt=attempted, last_success=attempted, error=None)
        atomic_json(path, payload)
        return payload
    if previous and not is_demo(previous) and valid_history(previous.get("history")):
        previous.update(status="stale", last_attempt=attempted, error=error or "invalid_or_empty_history")
        atomic_json(path, previous)
        return previous
    return {"history": [], "status": "unavailable", "last_attempt": attempted, "last_success": None, "error": error or "invalid_or_empty_history"}

def blank_snapshot():
    return {"meta": {"schema_version": "13.0", "demo": False, "generated_at": now(), "as_of": None, "universe_count": 0, "status": "unavailable"},
            "sources": {}, "methodology": {}, "market": {"regime": "Unavailable", "breadth": {}, "quality": {}},
            "tickers": [], "groups": [], "market_history": [], "today_changes": [], "signals_recent": [], "signal_scorecard": {},
            "macro_v8": {"fred": {}, "nyfed": {}, "market": {}, "regime": {}},
            "macro_v9": {"commodities": {"contracts": {}, "derived": {}, "breadth": {}}, "eia_inventories": {}, "calendar": {"events": []}},
            "revision_rankings": [], "signal_backtests": {}}

def validate_snapshot(snap):
    if is_demo(snap): raise ValueError("demo data is forbidden in production")
    if not isinstance(snap.get("tickers"), list) or not isinstance(snap.get("market"), dict): raise ValueError("invalid snapshot structure")
    seen = set()
    for x in snap["tickers"]:
        ticker = x.get("ticker")
        if not ticker or ticker in seen: raise ValueError("duplicate or missing ticker")
        seen.add(ticker)
        price = x.get("price", {}).get("close")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0: raise ValueError("invalid stock price")
    json.dumps(snap, allow_nan=False)
    return True
