
from __future__ import annotations
import numpy as np
import pandas as pd

HORIZONS = ((63, .40), (126, .20), (189, .20), (252, .20))

def weighted_momentum(close: pd.Series) -> float | None:
    close = close.dropna()
    if len(close) <= 252:
        return None
    last = float(close.iloc[-1])
    score = 0.0
    for days, w in HORIZONS:
        base = float(close.iloc[-1-days])
        score += ((last / base) - 1.0) * w
    return float(score)

def relative_line_change(stock: pd.Series, benchmark: pd.Series, days: int = 21) -> float | None:
    joined = pd.concat([stock.rename("s"), benchmark.rename("b")], axis=1).dropna()
    if len(joined) <= days:
        return None
    ratio = joined["s"] / joined["b"]
    return float(ratio.iloc[-1] / ratio.iloc[-1-days] - 1.0)

def percentile_1_99(values: dict[str, float | None]) -> dict[str, int | None]:
    valid = pd.Series({k: v for k, v in values.items() if v is not None and np.isfinite(v)})
    if valid.empty:
        return {k: None for k in values}
    pct = valid.rank(method="average", pct=True)
    mapped = {k: int(max(1, min(99, round(float(v) * 99)))) for k, v in pct.items()}
    return {k: mapped.get(k) for k in values}

def quadrant(long_rs: int | None, short_rs: int | None, threshold: int = 50) -> str:
    if long_rs is None or short_rs is None:
        return "unknown"
    if long_rs >= threshold and short_rs >= threshold:
        return "leading"
    if long_rs < threshold and short_rs >= threshold:
        return "improving"
    if long_rs >= threshold and short_rs < threshold:
        return "weakening"
    return "lagging"
