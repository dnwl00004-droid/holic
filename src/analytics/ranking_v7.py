
from __future__ import annotations
import math
from datetime import datetime, timezone

def clamp(x, lo=0, hi=100):
    return max(lo,min(hi,x))

def revision_score(est:dict)->dict:
    rp=(est or {}).get("revision_pulse") or {}
    ss=(est or {}).get("surprise_summary") or {}
    ch30=rp.get("change_30d_pct")
    ch90=rp.get("change_90d_pct")
    net=rp.get("net_30d")
    surprise=ss.get("avg_last4_pct")
    positive=ss.get("positive_last4")

    parts={}
    parts["30d_estimate_change"] = None if ch30 is None else clamp(50 + float(ch30)*5)
    parts["90d_estimate_change"] = None if ch90 is None else clamp(50 + float(ch90)*3)
    parts["revision_breadth"] = None if net is None else clamp(50 + float(net)*8)
    parts["surprise_history"] = None if surprise is None else clamp(50 + float(surprise)*2)
    parts["positive_surprises"] = None if positive is None else clamp(float(positive)/4*100)

    if any(v is None for v in parts.values()):
        return {"score":None,"direction":"Unavailable","components":parts,"coverage":sum(v is not None for v in parts.values()),"engine":"revision_score_v2","reason":"missing required inputs"}
    score=(
        parts["30d_estimate_change"]*.30 +
        parts["90d_estimate_change"]*.20 +
        parts["revision_breadth"]*.25 +
        parts["surprise_history"]*.15 +
        parts["positive_surprises"]*.10
    )
    direction="RISING" if score>=62 else "FALLING" if score<=38 else "MIXED"
    return {"score":round(score,1),"direction":direction,"components":{k:round(v,1) for k,v in parts.items()},
            "engine":"revision_score_v1"}

def expectation_gap(reverse_dcf:dict, earnings:dict)->dict:
    """
    Context-only comparison: current reported revenue YoY vs constant 5Y growth implied by reverse DCF.
    This is NOT a valuation verdict because quarterly YoY and 5Y constant growth are different horizons.
    """
    if not reverse_dcf or not reverse_dcf.get("available"):
        return {"available":False}
    implied=reverse_dcf.get("implied_revenue_growth_pct")
    actual=(earnings or {}).get("revenue_growth_yoy")
    if implied is None or actual is None:
        return {"available":False,"implied_growth_pct":implied,"reported_revenue_yoy_pct":actual}
    gap=float(actual)-float(implied)
    label="REPORTED_ABOVE_IMPLIED" if gap>=8 else "REPORTED_BELOW_IMPLIED" if gap<=-8 else "NEAR_IMPLIED"
    return {
        "available":True,
        "reported_revenue_yoy_pct":round(float(actual),2),
        "implied_5y_growth_pct":round(float(implied),2),
        "context_gap_pct":round(gap,2),
        "label":label,
        "caveat":"Quarterly reported YoY growth is compared with a constant 5Y implied growth assumption; use as context, not a valuation verdict."
    }

def catalyst_score(rec:dict)->dict:
    """
    0-100 descriptive catalyst score. No recommendation language.
    Layers are kept separate and visible.
    """
    v6=rec.get("v6") or {}
    v5=rec.get("v5") or {}
    est=v6.get("estimates") or {}
    rev=revision_score(est)
    ss=est.get("surprise_summary") or {}
    ins=v5.get("insider") or {}
    fq=v5.get("fundamental_quality") or {}
    tech=rec.get("screeners",{}).get("flags",{})
    changes=rec.get("_today_changes",[])

    # Revision 0..100
    revision=rev["score"]

    # Surprise
    sp=ss.get("avg_last4_pct")
    pos=ss.get("positive_last4")
    surprise=None if sp is None else clamp(50+float(sp)*2.5)
    if pos is not None and surprise is not None: surprise=(surprise*.65 + clamp(float(pos)/4*100)*.35)

    # Insider: only open-market P/S from Form 4
    buy=float(ins.get("purchase_value") or 0)
    sell=float(ins.get("sale_value") or 0)
    scale=max(buy+sell,1)
    insider=clamp(50 + 50*(buy-sell)/scale) if (buy+sell)>0 else 50 if "purchase_value" in ins and "sale_value" in ins else None

    # Technical event stack
    technical=50
    if tech.get("rs_new_high_before_price"): technical += 22
    elif tech.get("rs_new_high"): technical += 12
    if tech.get("volume_breakthrough"): technical += 12
    if tech.get("vcp_ready"): technical += 8
    if rec.get("entry",{}).get("label")=="READY": technical += 8
    technical=clamp(technical)

    # Fundamental quality is context, not catalyst timing, so low weight
    quality=float(fq["quality_score"]) if fq.get("quality_score") is not None else None
    if "screeners" not in rec:technical=None

    layers={"revision":revision,"surprise":surprise,"insider":insider,"technical":technical,"quality":quality}
    if any(v is None for v in layers.values()):
        return {"score":None,"state":"Unavailable","layers":layers,"revision_detail":rev,"engine":"catalyst_score_v2","reason":"missing required source layers"}
    total=revision*.30 + surprise*.15 + insider*.15 + technical*.30 + quality*.10
    return {
        "score":round(total,1),
        "state":"HIGH" if total>=72 else "ACTIVE" if total>=58 else "NEUTRAL" if total>=42 else "WEAK",
        "layers":{
            "revision":round(revision,1),
            "surprise":round(surprise,1),
            "insider":round(insider,1),
            "technical":round(technical,1),
            "quality":round(quality,1),
        },
        "revision_detail":rev,
        "engine":"catalyst_score_v1"
    }

def assign_cross_sectional_ranks(records:list[dict])->list[dict]:
    def rank(field):
        valid=[r for r in records if field(r) is not None]
        valid.sort(key=lambda r:field(r),reverse=True)
        n=len(valid)
        for i,r in enumerate(valid,1):
            yield r,i,n

    for r in records:
        r.setdefault("v7",{})
        r["v7"]["revision"]=revision_score((r.get("v6") or {}).get("estimates") or {})
        r["v7"]["expectation_gap"]=expectation_gap((r.get("v6") or {}).get("reverse_dcf") or {},r.get("earnings") or {})
        r["v7"]["catalyst"]=catalyst_score(r)

    for r,i,n in rank(lambda x:(x.get("v7") or {}).get("revision",{}).get("score")):
        r["v7"]["revision_rank"]=i
        r["v7"]["revision_percentile"]=round(100*(n-i)/max(n-1,1),1)
    for r,i,n in rank(lambda x:(x.get("v7") or {}).get("catalyst",{}).get("score")):
        r["v7"]["catalyst_rank"]=i
        r["v7"]["catalyst_percentile"]=round(100*(n-i)/max(n-1,1),1)
    return records
