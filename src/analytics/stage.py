
from __future__ import annotations
import pandas as pd

def stage_proxy(df: pd.DataFrame) -> dict:
    c = df["close"].dropna()
    if len(c) < 260:
        return {"value": None, "engine": "weinstein_proxy_v1"}
    ma50 = c.rolling(50).mean()
    ma200 = c.rolling(200).mean()
    px = float(c.iloc[-1])
    slope = float(ma200.iloc[-1] / ma200.iloc[-21] - 1.0)
    lo = float(c.iloc[-504:].min()) if len(c) >= 504 else float(c.min())
    hi = float(c.iloc[-504:].max()) if len(c) >= 504 else float(c.max())
    pos = (px - lo) / max(hi - lo, 1e-9)

    if px > ma200.iloc[-1] and ma50.iloc[-1] > ma200.iloc[-1] and slope > 0.005:
        stage = 2
    elif px < ma200.iloc[-1] and slope < -0.005:
        stage = 4
    elif abs(slope) <= 0.01 and pos < 0.55:
        stage = 1
    else:
        stage = 3
    return {"value": stage, "engine": "weinstein_proxy_v1", "ma200_slope_21d": slope, "range_position": pos}
