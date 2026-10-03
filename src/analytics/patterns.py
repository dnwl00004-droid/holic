
from __future__ import annotations
import numpy as np
import pandas as pd

def _pivots(series: pd.Series, order: int = 5):
    a = series.to_numpy(dtype=float)
    width=2*order+1
    if len(a)<width:
        return [],[]
    windows=np.lib.stride_tricks.sliding_window_view(a,width)
    centers=a[order:len(a)-order] if order else a
    # fmax/fmin preserve nanmax/nanmin semantics, including tied pivots.
    # Reduce all windows together instead of rescanning Python slices in replay.
    hi=np.flatnonzero(centers==np.fmax.reduce(windows,axis=1))+order
    lo=np.flatnonzero(centers==np.fmin.reduce(windows,axis=1))+order
    return [(int(i),a[i]) for i in hi],[(int(i),a[i]) for i in lo]

def vcp_proxy(df: pd.DataFrame) -> dict:
    if len(df) < 80:
        return {"detected": False, "score": 0}
    high = df["high"].dropna()
    low = df["low"].dropna()
    common = high.index.intersection(low.index)
    high, low = high.loc[common], low.loc[common]
    hs, _ = _pivots(high, 4)
    _, ls = _pivots(low, 4)
    swings = sorted([(i, "H", v) for i, v in hs] + [(i, "L", v) for i, v in ls])
    contractions = []
    for n in range(len(swings)-1):
        i1,t1,v1 = swings[n]
        i2,t2,v2 = swings[n+1]
        if t1 == "H" and t2 == "L" and i2 > i1:
            d = (v1-v2)/v1
            if 0.02 <= d <= 0.65:
                contractions.append((i1, i2, float(d), float(v1)))
    contractions = contractions[-4:]
    depths = [x[2] for x in contractions]
    decreasing = len(depths) >= 2 and all(depths[i+1] < depths[i] for i in range(len(depths)-1))
    last_ok = bool(depths and depths[-1] <= .15)
    first_ok = bool(depths and depths[0] <= .60)

    vol = df["volume"].dropna()
    dry = None
    if len(vol) >= 60 and vol.iloc[-60:-10].mean() > 0:
        dry = float(vol.iloc[-10:].mean() / vol.iloc[-60:-10].mean())

    pivot = float(max([x[3] for x in contractions[-2:]], default=df["high"].iloc[-20:].max()))
    px = float(df["close"].iloc[-1])
    distance = float((pivot-px)/pivot) if pivot else None

    score = 0
    if decreasing: score += 40
    if last_ok: score += 15
    if first_ok: score += 10
    if dry is not None and dry < .8: score += min(20, int((.8-dry)/.3*20))
    if distance is not None and -0.03 <= distance <= .10: score += 15
    detected = decreasing and last_ok and first_ok
    return {
        "detected": bool(detected),
        "score": int(max(0, min(100, score))),
        "contractions": [round(x, 4) for x in depths],
        "pivot": round(pivot, 4),
        "distance_pct": round(distance*100, 3) if distance is not None else None,
        "volume_dryup": round(dry, 3) if dry is not None else None,
        "engine": "vcp_proxy_v1",
    }

def double_bottom_proxy(df: pd.DataFrame) -> dict:
    c = df["close"].dropna().iloc[-140:]
    _, lows = _pivots(c, 4)
    if len(lows) < 2:
        return {"detected": False}
    (i1,l1),(i2,l2) = lows[-2], lows[-1]
    gap = i2-i1
    similarity = abs(l2/l1 - 1)
    between = float(c.iloc[i1:i2+1].max()) if i2 > i1 else 0
    rebound = between/min(l1,l2)-1 if min(l1,l2)>0 else 0
    ok = 15 <= gap <= 90 and similarity <= .10 and rebound >= .10
    return {"detected": bool(ok), "low_similarity_pct": round(similarity*100,2),
            "gap_days": int(gap), "mid_rebound_pct": round(rebound*100,2),
            "pivot": round(between,4) if between else None, "engine":"double_bottom_proxy_v1"}
