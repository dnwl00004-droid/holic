
from __future__ import annotations
import pandas as pd

def breadth(price_map: dict[str, pd.DataFrame]) -> dict:
    eligible50 = eligible200 = above50 = above200 = 0
    for df in price_map.values():
        c = df.get("close", pd.Series(dtype=float)).dropna()
        if len(c) >= 50:
            eligible50 += 1
            above50 += int(c.iloc[-1] > c.iloc[-50:].mean())
        if len(c) >= 200:
            eligible200 += 1
            above200 += int(c.iloc[-1] > c.iloc[-200:].mean())
    return {
        "above_50": round(100*above50/eligible50, 1) if eligible50 else None,
        "above_200": round(100*above200/eligible200, 1) if eligible200 else None,
        "eligible_50": eligible50,
        "eligible_200": eligible200,
    }

def distribution_pressure(benchmark: pd.DataFrame, lookback: int = 25) -> dict:
    df = benchmark.dropna(subset=["close","volume"]).tail(lookback+1)
    if len(df) < 2:
        return {"count": None}
    ret = df["close"].pct_change()
    prev_vol = df["volume"].shift(1)
    events = (ret <= -0.002) & (df["volume"] > prev_vol)
    return {"count": int(events.tail(lookback).sum()), "engine":"distribution_proxy_v1"}

def regime(benchmark: pd.DataFrame, breadth_200: float | None, dist_count: int | None) -> str:
    c = benchmark["close"].dropna()
    if len(c) < 220:
        return "UNKNOWN"
    ma50, ma200 = c.rolling(50).mean(), c.rolling(200).mean()
    px = c.iloc[-1]
    slope200 = ma200.iloc[-1] / ma200.iloc[-21] - 1
    if px > ma50.iloc[-1] > ma200.iloc[-1] and slope200 > 0 and (breadth_200 or 0) >= 55 and (dist_count or 0) < 5:
        return "UPTREND"
    if px < ma200.iloc[-1] and slope200 < 0:
        return "DOWNTREND"
    return "PRESSURE"
