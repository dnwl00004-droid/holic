
from __future__ import annotations
import pandas as pd
import yfinance as yf

def download_daily(tickers: list[str], period: str = "3y") -> dict[str, pd.DataFrame]:
    """Download adjusted OHLCV in batches and normalize to per-ticker DataFrames."""
    raw = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=True,
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
                result[t] = df
        except Exception:
            continue
    return result
