
from __future__ import annotations
def clamp(x,lo=0,hi=100):return max(lo,min(hi,x))
def v(data,key,default=None):return ((data or {}).get(key) or {}).get("value",default)

def macro_scores(fred,nyfed=None,gdpnow=None,market=None):
    gp=[]
    if (gdpnow or {}).get("value") is not None:gp.append(clamp(50+(gdpnow["value"]-2)*10))
    if v(fred,"PAYEMS") is not None:gp.append(clamp(50+v(fred,"PAYEMS")/30))
    for x,w in [(v(fred,"INDPRO"),6),(v(fred,"RSAFS"),4),(v(fred,"HOUST"),2)]:
        if x is not None:gp.append(clamp(50+x*w))
    if v(fred,"UNRATE") is not None:gp.append(clamp(75-(v(fred,"UNRATE")-4)*18))
    growth=sum(gp)/len(gp) if gp else None
    ip=[]
    for x,target,w in [(v(fred,"CPIAUCSL"),2,15),(v(fred,"CPILFESL"),2,15),(v(fred,"PCEPILFE"),2,18),(v(fred,"T10YIE"),2.2,20)]:
        if x is not None:ip.append(clamp(50+(x-target)*w))
    inflation=sum(ip)/len(ip) if ip else None
    lp=[]
    if v(fred,"M2SL") is not None:lp.append(clamp(50+v(fred,"M2SL")*5))
    for key,scale,sign in [("WALCL",100,1),("WRESBAL",100,1),("RRPONTSYD",50,-1),("WTREGEN",100,-1)]:
        ch=(fred.get(key) or {}).get("change_3m_raw")
        if ch is not None:
            if (fred.get(key) or {}).get("transform")=="millions_to_bn": ch=ch/1000
            lp.append(clamp(50+sign*ch/scale*10))
    liquidity=sum(lp)/len(lp) if lp else None
    cp=[]
    if v(fred,"BAMLH0A0HYM2") is not None:cp.append(clamp(100-(v(fred,"BAMLH0A0HYM2")-2)*18))
    if v(fred,"BAMLC0A0CM") is not None:cp.append(clamp(100-(v(fred,"BAMLC0A0CM")-.7)*35))
    credit=sum(cp)/len(cp) if cp else None
    rp=[]
    if v(fred,"DFF") is not None:rp.append(clamp(35+v(fred,"DFF")*10))
    if v(fred,"DFII10") is not None:rp.append(clamp(40+v(fred,"DFII10")*18))
    if v(fred,"T10Y2Y") is not None:rp.append(clamp(50-v(fred,"T10Y2Y")*10))
    rates=sum(rp)/len(rp) if rp else None
    basis=((nyfed or {}).get("SOFR_EFFR_SPREAD_BP") or {}).get("value")
    funding=None if basis is None else clamp(50+abs(float(basis))*3)
    rnd=lambda x: None if x is None else round(x,1)
    axes={"growth":rnd(growth),"inflation":rnd(inflation),"liquidity":rnd(liquidity),
          "credit":rnd(credit),"rates_pressure":rnd(rates),"funding_stress":rnd(funding)}
    gh=growth is not None and growth>=50;ih=inflation is not None and inflation>=50
    regime="GOLDILOCKS" if gh and not ih else "REFLATION" if gh and ih else "STAGFLATION" if (not gh and ih) else "DISINFLATION_SLOWDOWN"
    if growth is None or inflation is None: regime="Unavailable"
    risk=None if any(x is None for x in (rates,credit,liquidity,growth,funding)) else rates*.30+(100-credit)*.25+(100-liquidity)*.20+(100-growth)*.20+funding*.05
    return {"axes":axes,"regime":regime,"macro_risk_score":rnd(risk),
            "risk_state":"Unavailable" if risk is None else "HIGH" if risk>=68 else "ELEVATED" if risk>=55 else "BALANCED" if risk>=40 else "SUPPORTIVE",
            "coverage":{ "growth":len(gp),"inflation":len(ip),"liquidity":len(lp),"credit":len(cp),"rates_pressure":len(rp),"funding_stress":int(basis is not None)},
            "engine":"macro_regime_v2"}

SENS={"Technology":(.5,-1,1,.4,-1),"Communication Services":(.5,-.5,.7,.3,-.5),
"Consumer Discretionary":(1,-.4,.4,.5,-.5),"Consumer Staples":(-.4,-.1,0,.1,.1),"Materials":(.8,.8,.2,.3,0),"Health Care":(-.2,-.1,.1,.2,-.1),
"Consumer Cyclical":(1,-.4,.4,.5,-.5),"Consumer Defensive":(-.4,-.1,0,.1,.1),
"Financial Services":(.5,.2,-.1,1,.2),"Financials":(.5,.2,-.1,1,.2),"Energy":(.5,1,.1,.2,.1),
"Industrials":(1,.1,.2,.4,-.2),"Basic Materials":(.8,.8,.2,.3,0),"Healthcare":(-.2,-.1,.1,.2,-.1),
"Utilities":(-.3,-.2,.3,.2,-1),"Real Estate":(.1,-.4,.7,.5,-1.2)}

def sector_macro_fit(sector,macro):
    a=macro.get("axes",{});co=SENS.get(sector);keys=["growth","inflation","liquidity","credit","rates_pressure"]
    if co is None or any(a.get(k) is None for k in keys):
        return {"score":None,"state":"Unavailable","reason":"missing axes or unsupported sector"}
    raw=sum(((a.get(k,50)-50)/50)*c for k,c in zip(keys,co));score=clamp(50+raw*22)
    return {"score":round(score,1),"state":"TAILWIND" if score>=62 else "HEADWIND" if score<=38 else "NEUTRAL",
            "engine":"sector_macro_sensitivity_v1","note":"Heuristic sensitivity context, not a return forecast."}
