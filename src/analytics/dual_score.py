
from __future__ import annotations

def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))

def strength_score(rs, short_rs, trend, stage):
    """Structural leadership: RS + trend + stage."""
    rs = rs or 0
    short_rs = short_rs or 0
    trend_pct = 100 * trend.get("passed", 0) / max(trend.get("total", 8), 1)
    stage_bonus = {2: 100, 1: 55, 3: 45, 4: 10}.get(stage.get("value"), 25)
    return int(round(clamp(rs*.45 + short_rs*.20 + trend_pct*.25 + stage_bonus*.10)))

def setup_score(vcp, double_bottom):
    """Actionability: pattern quality, pivot proximity and volume contraction."""
    v = float(vcp.get("score", 0) or 0)
    dist = vcp.get("distance_pct")
    dry = vcp.get("volume_dryup")
    pivot_component = 0
    if dist is not None:
        if -2 <= dist <= 3: pivot_component = 100
        elif 3 < dist <= 7: pivot_component = 80
        elif 7 < dist <= 12: pivot_component = 55
        elif -5 <= dist < -2: pivot_component = 45
        else: pivot_component = 15
    vol_component = 25
    if dry is not None:
        vol_component = clamp((1.05 - float(dry)) / .55 * 100)
    pattern_bonus = 100 if vcp.get("detected") else (70 if double_bottom.get("detected") else 25)
    return int(round(clamp(v*.45 + pivot_component*.25 + vol_component*.15 + pattern_bonus*.15)))

def radar_axes(rs, trend, setup, earnings):
    trend_pct = 100 * trend.get("passed", 0) / max(trend.get("total", 8), 1)
    growths = [earnings.get("eps_growth_yoy"), earnings.get("revenue_growth_yoy")]
    growths = [g for g in growths if g is not None]
    growth = 50 if not growths else clamp(sum(clamp(float(g), -20, 80) for g in growths)/len(growths) + 20)
    dry = setup.get("volume_dryup")
    volume = 50 if dry is None else clamp((1.15 - float(dry))/.7*100)
    return {
        "RS": int(clamp(rs or 0)),
        "Trend": int(clamp(trend_pct)),
        "Setup": int(clamp(setup.get("score", 0) or 0)),
        "Growth": int(clamp(growth)),
        "Volume": int(clamp(volume)),
    }

def status_label(strength, setup, vcp):
    dist = vcp.get("distance_pct")
    if strength >= 78 and setup >= 78 and (dist is None or -2 <= dist <= 7):
        return "READY"
    if strength >= 72 and setup >= 55:
        return "WATCH"
    if strength >= 72 and dist is not None and dist < -5:
        return "EXTENDED"
    if strength < 50:
        return "WEAK"
    return "WATCH"
