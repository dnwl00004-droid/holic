"""Validated public Nasdaq daily quotes. Price returns do not include dividends."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Lock, local
import math
import re
import time

import pandas as pd
import requests

from ..reliability import atomic_json, now, read_json

SOURCE = "Nasdaq historical quotes"
METHOD = "Provider-reported split-adjusted daily OHLCV; price returns exclude cash dividends"
API = "https://api.nasdaq.com/api/quote/{symbol}/historical"
CACHE = Path(__file__).resolve().parents[2] / "data/cache/nasdaq"
ETF_SYMBOLS = {"SPY", "TLT", "HYG", "GLD", "SLV", "CPER", "USO", "BNO", "UNG", "DBA", "CORN", "WEAT", "SOYB", "PPLT", "PALL", "COPX", "URA"}
_circuit = Event()
_gate = Lock()
_next_request = 0.0
_clients = local()


class QuoteError(ValueError):
    pass


class QuoteFrames(dict):
    def __init__(self):
        super().__init__()
        self.errors={}


def _number(value):
    if isinstance(value, bool) or value is None:
        raise QuoteError("invalid_numeric_quote")
    try:
        number = float(str(value).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        raise QuoteError("invalid_numeric_quote") from None
    if not math.isfinite(number):
        raise QuoteError("nonfinite_quote")
    return number


def _symbol(value):
    return re.sub(r"[./-]", "", str(value).upper())


def parse_quotes(payload, expected_symbol):
    """Reject wrong instruments, incomplete pagination and malformed OHLCV."""
    if not isinstance(payload, dict) or payload.get("status", {}).get("rCode") != 200:
        raise QuoteError("nasdaq_api_error")
    data = payload.get("data") or {}
    if _symbol(data.get("symbol")) != _symbol(expected_symbol):
        raise QuoteError("symbol_mismatch")
    rows = (data.get("tradesTable") or {}).get("rows") or []
    if not rows:
        raise QuoteError("no_daily_quotes")
    try:
        total = int(str(data["totalRecords"]).replace(",", ""))
    except (KeyError, ValueError, TypeError):
        raise QuoteError("missing_record_count") from None
    if total != len(rows):
        raise QuoteError("incomplete_history_page")
    bars = []
    dates = set()
    for row in rows:
        try:
            day = datetime.strptime(row["date"], "%m/%d/%Y").date()
        except (KeyError, TypeError, ValueError):
            raise QuoteError("invalid_quote_date") from None
        if day > datetime.now(timezone.utc).date() or day.weekday() >= 5 or day in dates:
            raise QuoteError("invalid_or_duplicate_session")
        dates.add(day)
        bar = {key: _number(row.get(key)) for key in ("open", "high", "low", "close")}
        volume=row.get("volume")
        bar["volume"]=math.nan if volume is None or str(volume).strip().upper() in ("N/A","NA","--","—","") else _number(volume)
        if min(bar[k] for k in ("open", "high", "low", "close")) <= 0 or not math.isnan(bar["volume"]) and (bar["volume"] < 0 or not bar["volume"].is_integer()):
            raise QuoteError("invalid_quote_range")
        tolerance = max(bar["high"] * 1e-6, 1e-6)
        if bar["low"] > min(bar["open"], bar["close"]) + tolerance or bar["high"] < max(bar["open"], bar["close"]) - tolerance or bar["high"] < bar["low"]:
            raise QuoteError("inconsistent_ohlc")
        bars.append({"date": day.isoformat(), **bar})
    frame = pd.DataFrame(bars).set_index("date").sort_index()
    frame.index = pd.to_datetime(frame.index)
    frame.attrs["missing_volume_sessions"]=int(frame["volume"].isna().sum())
    # Such discontinuities can be unadjusted splits/spin-offs; omit from rankings.
    if (frame["close"].pct_change(fill_method=None).abs() > 0.65).any():
        raise QuoteError("large_price_discontinuity_requires_review")
    return frame


def _cached_frame(cached, ticker):
    if not isinstance(cached, dict) or cached.get("source") != SOURCE or cached.get("symbol") != ticker:
        return None
    try:
        frame = parse_quotes(cached["payload"], ticker)
        frame.attrs.update({key: cached.get(key) for key in ("source", "source_url", "method", "fetched_at", "requested_start")})
        return frame
    except (QuoteError, KeyError):
        return None


def fetch_daily(ticker, years=3, cache_dir=CACHE, session=None):
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", ticker):
        raise QuoteError("unsupported_nasdaq_instrument")
    path = Path(cache_dir) / (ticker + ".json")
    cached = read_json(path, {})
    prior = _cached_frame(cached, ticker)
    failure_path=Path(cache_dir)/"failures"/(ticker+".json")
    failure=read_json(failure_path,{})
    if prior is None and failure.get("last_attempt"):
        try:
            failed_age=(datetime.now(timezone.utc)-datetime.fromisoformat(failure["last_attempt"])).total_seconds()
        except (TypeError,ValueError):
            failed_age=math.inf
        if 0<=failed_age<15*60 and failure.get("error"):
            raise QuoteError(failure["error"])
    today = datetime.now(timezone.utc).date()
    start = (pd.Timestamp(today) - pd.DateOffset(years=years)).date().isoformat()
    enough_range = cached.get("requested_start", "9999") <= start
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(cached["fetched_at"])).total_seconds()
    except (KeyError, TypeError, ValueError):
        age = math.inf
    if prior is not None and enough_range and age < 6 * 3600 and not cached.get("error"):
        prior.attrs.update(status="ok", error=None)
        return prior
    try:
        if _circuit.is_set():
            raise QuoteError("nasdaq_circuit_open")
        global _next_request
        with _gate:
            delay = max(0.0, _next_request - time.monotonic())
            if delay:
                time.sleep(delay)
            _next_request = time.monotonic() + 0.25
        symbol=ticker.replace("-",".") if ticker in ("BRK-B","BF-B") else ticker
        if session is None:
            if not hasattr(_clients,"session"):_clients.session=requests.Session()
            session=_clients.session
        response = session.get(API.format(symbol=symbol), params={
            "assetclass": "etf" if ticker in ETF_SYMBOLS else "stocks",
            "fromdate": start, "todate": (today + timedelta(days=1)).isoformat(),
            "limit": min(4000, years * 270 + 100),
        }, headers={"User-Agent": "RS-Radar/15 personal research dashboard", "Accept": "application/json"}, timeout=(8, 12))
        if response.status_code in (401, 403, 429):
            _circuit.set()
        response.raise_for_status()
        payload = response.json()
        frame = parse_quotes(payload, ticker)
        if prior is not None and enough_range and (frame.index[0] > prior.index[0] or frame.index[-1] < prior.index[-1]):
            raise QuoteError("quote_history_regression")
        asset = "etf" if ticker in ETF_SYMBOLS else "stocks"
        metadata = {"symbol": ticker, "source": SOURCE, "source_url": f"https://www.nasdaq.com/market-activity/{asset}/{ticker.lower()}/historical",
                    "method": METHOD, "requested_start": start, "fetched_at": now(), "payload": payload, "error": None}
        atomic_json(path, metadata)
        frame.attrs.update({key: metadata[key] for key in ("source", "source_url", "method", "fetched_at", "requested_start")})
        frame.attrs.update(status="ok", error=None)
        return frame
    except (requests.RequestException, ValueError) as error:
        code = str(error) if isinstance(error, QuoteError) else type(error).__name__
        status = getattr(getattr(error, "response", None), "status_code", None)
        if status:
            code += ":" + str(status)
        if prior is None:
            if isinstance(error,QuoteError) and code not in ("nasdaq_circuit_open",):
                atomic_json(failure_path,{"error":code,"last_attempt":now()})
            raise QuoteError(code) from None
        prior.attrs.update(status="stale", error=code)
        return prior


def download_daily(tickers, period="3y", workers=4, cache_dir=CACHE):
    match = re.fullmatch(r"(\d+)y", period)
    years = int(match.group(1)) if match else 5 if period == "max" else 3
    # Public quote history is bounded. Export actual coverage rather than promise MAX.
    years = min(max(years, 1), 5)
    result = QuoteFrames()
    retry=[]
    def fetch(ticker):
        try:
            return ticker, fetch_daily(ticker, years, cache_dir)
        except QuoteError as error:
            result.errors[ticker]=str(error)
            if str(error) in ("ReadTimeout","ConnectTimeout","ConnectionError"):retry.append(ticker)
            print(f"[quotes] {ticker}: {error}", flush=True)
            return ticker, None
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for ticker, frame in pool.map(fetch, dict.fromkeys(tickers)):
            if frame is not None:
                result.errors.pop(ticker,None)
                result[ticker] = frame
        pending=list(retry);retry.clear()
        if pending and not _circuit.is_set():
            # Retry a transport failure once; never retry 429/403 or invalid prices.
            for ticker,frame in pool.map(fetch,pending):
                if frame is not None:
                    result.errors.pop(ticker,None)
                    result[ticker]=frame
    return result
