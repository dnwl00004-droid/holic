
from __future__ import annotations
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone

def download_daily(tickers: list[str], period: str = "3y", auto_adjust: bool = True) -> dict[str, pd.DataFrame]:
    """Download daily OHLCV and preserve whether cash dividends were adjusted."""
    if not tickers: return {}
    # One explicit failure ends this provider batch; do not hammer a 429 endpoint.
    probe = yf.Ticker(tickers[0]).history(period=period, interval="1d", auto_adjust=auto_adjust, repair=True, timeout=15, raise_errors=True)
    if probe.empty: return {}
    if len(tickers) == 1:
        probe.columns = [str(c).lower().replace(" ", "_") for c in probe.columns]
        probe.attrs.update(source="Yahoo Finance",source_url="https://finance.yahoo.com/quote/"+tickers[0],method="Yahoo daily OHLCV; dividend-adjusted" if auto_adjust else "Yahoo daily OHLCV; close excludes cash dividends",status="ok",fetched_at=datetime.now(timezone.utc).isoformat())
        return {tickers[0]:probe.dropna(subset=["close"])}
    raw = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=auto_adjust,
        repair=True,
        group_by="ticker",
        threads=4,
        progress=False,
        timeout=20,
    )
    result: dict[str, pd.DataFrame] = {}
    if len(tickers) == 1 and not isinstance(raw.columns,pd.MultiIndex):
        df = raw.copy()
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        result[tickers[0]] = df.dropna(how="all")
        return result

    for t in tickers:
        try:
            if isinstance(raw.columns,pd.MultiIndex):
                level=next(i for i in range(raw.columns.nlevels) if t in raw.columns.get_level_values(i))
                df=raw.xs(t,axis=1,level=level).copy()
            else:
                df=raw.copy()
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            df = df.dropna(subset=["close"]).sort_index()
            df=df[~df.index.duplicated(keep="last")]
            if not df.empty:
                df.attrs.update(source="Yahoo Finance",source_url="https://finance.yahoo.com/quote/"+t,method="Yahoo daily OHLCV; dividend-adjusted" if auto_adjust else "Yahoo daily OHLCV; close excludes cash dividends",status="ok",fetched_at=datetime.now(timezone.utc).isoformat())
                result[t] = df
        except Exception:
            continue
    return result
