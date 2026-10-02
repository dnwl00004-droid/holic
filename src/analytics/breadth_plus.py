
from __future__ import annotations
import math
import numpy as np
import pandas as pd

def _safe_pct(num, den):
    return round(100*num/den, 1) if den else None

def _ema(values: pd.Series, span: int):
    return values.ewm(span=span, adjust=False).mean()

def market_breadth_plus(price_map: dict[str, pd.DataFrame], benchmark: pd.DataFrame) -> dict:
    """
    Cross-sectional breadth metrics derived only from OHLCV.
    Includes StockBee-style counts and a Zweig-style breadth-thrust proxy.
    """
    stats = {
        "eligible": 0, "adv": 0, "dec": 0, "flat": 0,
        "above20": 0, "above40": 0, "above50": 0, "above200": 0,
        "new_high_52w": 0, "new_low_52w": 0,
        "up4": 0, "down4": 0, "up25_q": 0, "down25_q": 0,
        "up_volume": 0.0, "down_volume": 0.0,
        "atr_ext_up": 0, "atr_ext_down": 0,
    }
    adv_history = []
    # Align on benchmark trading dates for historical advance %
    bench_dates = pd.DatetimeIndex(benchmark.index[-40:])
    for d in bench_dates:
        adv = dec = 0
        for df in price_map.values():
            if d not in df.index:
                continue
            loc = df.index.get_loc(d)
            if not isinstance(loc, (int, np.integer)) or loc < 1:
                continue
            c0, c1 = float(df["close"].iloc[loc]), float(df["close"].iloc[loc-1])
            if c0 > c1: adv += 1
            elif c0 < c1: dec += 1
        denom = adv + dec
        adv_history.append((d, adv/denom if denom else np.nan))

    for df in price_map.values():
        if not {"close","high","low","volume"}.issubset(df.columns):
            continue
        d = df.dropna(subset=["close","volume"])
        if len(d) < 252:
            continue
        stats["eligible"] += 1
        c = d["close"]
        px, prev = float(c.iloc[-1]), float(c.iloc[-2])
        day_ret = px/prev - 1
        vol = float(d["volume"].iloc[-1] or 0)

        if day_ret > 0:
            stats["adv"] += 1
            stats["up_volume"] += vol
        elif day_ret < 0:
            stats["dec"] += 1
            stats["down_volume"] += vol
        else:
            stats["flat"] += 1

        for n, key in [(20,"above20"),(40,"above40"),(50,"above50"),(200,"above200")]:
            if px > float(c.tail(n).mean()):
                stats[key] += 1

        hi52, lo52 = float(c.tail(252).max()), float(c.tail(252).min())
        if px >= hi52 * 0.995: stats["new_high_52w"] += 1
        if px <= lo52 * 1.005: stats["new_low_52w"] += 1
        if day_ret >= .04: stats["up4"] += 1
        if day_ret <= -.04: stats["down4"] += 1
        qret = px/float(c.iloc[-64]) - 1
        if qret >= .25: stats["up25_q"] += 1
        if qret <= -.25: stats["down25_q"] += 1

        # ATR extension from 20DMA in ATR units
        prev_c = c.shift(1)
        tr = pd.concat([
            (d["high"]-d["low"]).abs(),
            (d["high"]-prev_c).abs(),
            (d["low"]-prev_c).abs()
        ], axis=1).max(axis=1)
        atr = float(tr.tail(14).mean())
        ma20 = float(c.tail(20).mean())
        if atr > 0:
            ext = (px-ma20)/atr
            if ext >= 3: stats["atr_ext_up"] += 1
            if ext <= -3: stats["atr_ext_down"] += 1

    n=stats["eligible"]
    uv, dv = stats["up_volume"], stats["down_volume"]
    ad_denom=stats["adv"]+stats["dec"]
    adv_pct = stats["adv"]/ad_denom if ad_denom else None

    hist_series = pd.Series(
        [v for _,v in adv_history],
        index=[d for d,_ in adv_history],
        dtype=float
    ).dropna()
    thrust = float(_ema(hist_series, 10).iloc[-1]*100) if len(hist_series) else None

    return {
        "eligible": n,
        "advance": stats["adv"],
        "decline": stats["dec"],
        "flat": stats["flat"],
        "advance_pct": round(adv_pct*100,1) if adv_pct is not None else None,
        "ad_ratio": round(stats["adv"]/max(stats["dec"],1),2),
        "up_down_volume_ratio": round(uv/max(dv,1),2),
        "above_20": _safe_pct(stats["above20"],n),
        "above_40": _safe_pct(stats["above40"],n),
        "above_50": _safe_pct(stats["above50"],n),
        "above_200": _safe_pct(stats["above200"],n),
        "new_high_52w": stats["new_high_52w"],
        "new_low_52w": stats["new_low_52w"],
        "new_high_low_net": stats["new_high_52w"]-stats["new_low_52w"],
        "up_4pct": stats["up4"],
        "down_4pct": stats["down4"],
        "daily_4pct_ratio": round(stats["up4"]/max(stats["down4"],1),2),
        "up_25pct_quarter": stats["up25_q"],
        "down_25pct_quarter": stats["down25_q"],
        "quarter_bull_bear_ratio": round(stats["up25_q"]/max(stats["down25_q"],1),2),
        "atr_3x_extended_up": stats["atr_ext_up"],
        "atr_3x_extended_down": stats["atr_ext_down"],
        "breadth_thrust_10ema": round(thrust,1) if thrust is not None else None,
        "breadth_thrust_flag": bool(thrust is not None and thrust >= 61.5),
        "advance_history": [{"date":d.strftime("%Y-%m-%d"),"advance_pct":round(v*100,1)}
                            for d,v in adv_history if np.isfinite(v)][-20:],
        "engine": "breadth_plus_v1"
    }

def market_quality_score(b: dict, benchmark: pd.DataFrame) -> dict:
    """
    Transparent 0-100 market-quality composite:
    Breadth 40, trend 30, momentum 20, participation/volume 10.
    Descriptive signal only.
    """
    c=benchmark["close"].dropna()
    if len(c)<220:
        return {"score":None,"state":"UNKNOWN"}
    px=float(c.iloc[-1])
    ma20=float(c.tail(20).mean()); ma50=float(c.tail(50).mean()); ma200=float(c.tail(200).mean())
    ret20=px/float(c.iloc[-22])-1 if len(c)>22 else 0
    breadth = (
        (b.get("above_50") or 0)*.20 +
        (b.get("above_200") or 0)*.15 +
        min(100,max(0,(b.get("advance_pct") or 50)))*.05
    )
    trend = (10 if px>ma20 else 0)+(10 if px>ma50 else 0)+(10 if px>ma200 else 0)
    momentum = max(0,min(20,10 + ret20*100))
    uv=b.get("up_down_volume_ratio") or 1
    participation=max(0,min(10, 5 + math.log(max(uv,.05))*3))
    score=int(round(max(0,min(100,breadth+trend+momentum+participation))))
    state = "STRONG" if score>=75 else "HEALTHY" if score>=60 else "MIXED" if score>=45 else "WEAK"
    return {"score":score,"state":state,
            "components":{"breadth":round(breadth,1),"trend":trend,"momentum":round(momentum,1),"participation":round(participation,1)},
            "engine":"market_quality_v1"}
