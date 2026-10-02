
from __future__ import annotations

def score(rs: int|None, short_rs: int|None, trend: dict, vcp: dict, earnings_growth: float|None=None) -> int:
    # Transparent discovery score; weights can be changed without changing source data.
    s = 0.0
    s += (rs or 0) / 99 * 25
    s += (short_rs or 0) / 99 * 15
    s += (trend.get("passed",0) / max(trend.get("total",8),1)) * 15
    s += min(vcp.get("score",0),100) / 100 * 20
    dist = vcp.get("distance_pct")
    if dist is not None:
        if -3 <= dist <= 5: s += 10
        elif 5 < dist <= 10: s += 6
        elif -8 <= dist < -3: s += 4
    dry = vcp.get("volume_dryup")
    if dry is not None:
        s += max(0, min(5, (1-dry)*10))
    if earnings_growth is not None:
        s += max(0, min(10, earnings_growth/50*10))
    return int(round(max(0,min(100,s))))
