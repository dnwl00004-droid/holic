
from __future__ import annotations
import pandas as pd

def trend_template(df: pd.DataFrame, rs_score: int | None, rs_floor: int = 70) -> dict:
    c = df["close"].dropna()
    if len(c) < 252:
        return {"passed": 0, "total": 8, "checks": {}}

    ma50 = c.rolling(50).mean()
    ma150 = c.rolling(150).mean()
    ma200 = c.rolling(200).mean()
    px = float(c.iloc[-1])
    low52, high52 = float(c.iloc[-252:].min()), float(c.iloc[-252:].max())
    rising200 = len(ma200.dropna()) >= 21 and ma200.iloc[-1] > ma200.iloc[-21]

    checks = {
        "price_above_150_200": px > ma150.iloc[-1] and px > ma200.iloc[-1],
        "ma150_above_200": ma150.iloc[-1] > ma200.iloc[-1],
        "ma200_rising": bool(rising200),
        "ma50_above_150_200": ma50.iloc[-1] > ma150.iloc[-1] and ma50.iloc[-1] > ma200.iloc[-1],
        "price_above_50": px > ma50.iloc[-1],
        "above_52w_low_30pct": px >= low52 * 1.30,
        "within_25pct_52w_high": px >= high52 * 0.75,
        "rs_above_floor": (rs_score or 0) >= rs_floor,
    }
    return {"passed": sum(bool(v) for v in checks.values()), "total": len(checks), "checks": checks}
