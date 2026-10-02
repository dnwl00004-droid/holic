
from __future__ import annotations
from collections import defaultdict

def analyze_portfolio(holdings:list[dict], snapshot:dict):
    by={x["ticker"].upper():x for x in snapshot.get("tickers",[])}
    rows=[]; total=0
    for h in holdings:
        t=str(h["ticker"]).upper();shares=float(h.get("shares",0));cost=h.get("cost_basis")
        rec=by.get(t)
        if not rec:continue
        px=float(rec["price"]["close"]);value=shares*px;total+=value
        rows.append({"ticker":t,"shares":shares,"price":px,"value":value,"cost_basis":cost,
                     "sector":rec.get("sector"),"strength":rec.get("scores",{}).get("strength"),
                     "entry":rec.get("scores",{}).get("entry"),"rs":rec.get("rs",{}).get("score")})
    sectors=defaultdict(float)
    for r in rows:sectors[r["sector"]]+=r["value"]
    for r in rows:r["weight_pct"]=round(100*r["value"]/total,2) if total else 0
    sector_weights={k:round(100*v/total,2) for k,v in sectors.items()} if total else {}
    hhi=sum((r["weight_pct"]/100)**2 for r in rows)
    top_weight=max((r["weight_pct"] for r in rows),default=0)
    weighted_rs=sum((r["rs"] or 0)*r["value"] for r in rows)/total if total else None
    weighted_strength=sum((r["strength"] or 0)*r["value"] for r in rows)/total if total else None
    return {"total_value":round(total,2),"holdings":rows,"sector_weights":sector_weights,
            "concentration_hhi":round(hhi,4),"largest_position_pct":round(top_weight,2),
            "weighted_rs":round(weighted_rs,1) if weighted_rs is not None else None,
            "weighted_strength":round(weighted_strength,1) if weighted_strength is not None else None}
