"""Instrument-aware adapters; never label ETF proxies as futures prices."""
from datetime import datetime, timezone
import math

import pandas as pd

from .nasdaq import download_daily as nasdaq_daily
from .nasdaq import ETF_SYMBOLS
from .yahoo import download_daily as yahoo_daily


class PriceFrames(dict):
    def __init__(self):
        super().__init__()
        self.errors = {}


def _verified_etf_fallback(frame):
    """Accept an independent dividend-excluding ETF feed only with coherent bars."""
    if frame is None or len(frame) < 252 or not isinstance(frame.index, pd.DatetimeIndex):
        return False
    dates = frame.index.tz_localize(None) if frame.index.tz is not None else frame.index
    if dates.has_duplicates or not dates.is_monotonic_increasing:
        return False
    if dates[-1].date() > datetime.now(timezone.utc).date() or (datetime.now(timezone.utc).date() - dates[-1].date()).days > 10:
        return False
    if not set(("open", "high", "low", "close")) <= set(frame.columns):
        return False
    bars = frame[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
    if bars.isna().any().any() or not bars.map(math.isfinite).all().all() or (bars <= 0).any().any():
        return False
    tolerance = bars["high"] * 1e-6 + 1e-6
    if ((bars["low"] > bars[["open", "close"]].min(axis=1) + tolerance) |
        (bars["high"] < bars[["open", "close"]].max(axis=1) - tolerance) |
        (bars["high"] < bars["low"])).any():
        return False
    return not (bars["close"].pct_change(fill_method=None).abs() > 0.65).any()


def download_daily(tickers, period="3y"):
    equity = [t for t in tickers if not any(c in t for c in "=^") and t not in ("DX-Y.NYB", "BTC-USD")]
    other = [t for t in tickers if t not in equity]
    result = PriceFrames()
    if equity:
        quotes=nasdaq_daily(equity, period)
        result.update(quotes)
        result.errors.update(getattr(quotes,"errors",{}))
        # A few ETF histories have contradictory OHLC rows at Nasdaq. Query a
        # separate feed only for those instruments; keep all other failures.
        rejected = [t for t in equity if t in ETF_SYMBOLS and t != "SPY" and result.errors.get(t)=="inconsistent_ohlc"]
        if rejected:
            try:
                fallback = yahoo_daily(rejected, period, auto_adjust=False)
                for ticker in rejected:
                    frame = fallback.get(ticker)
                    if _verified_etf_fallback(frame):
                        result[ticker] = frame
                        result.errors.pop(ticker, None)
            except Exception:
                pass
    if other:
        try:
            result.update(yahoo_daily(other, period))
        except Exception as error:
            # Keep a safe, actionable module identifier in Data Health. The
            # exception message may include provider URLs or account data.
            missing = getattr(error, "name", None) if isinstance(error, ModuleNotFoundError) else None
            code = "rate_limited_429" if type(error).__name__ == "YFRateLimitError" else type(error).__name__
            if missing and missing.replace("_", "").replace(".", "").isalnum():
                code += ":" + missing[:80]
            for ticker in other:
                result.errors[ticker] = code
    return result
