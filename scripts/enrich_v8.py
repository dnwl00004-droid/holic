
from __future__ import annotations
import argparse,json
from pathlib import Path
import requests
from src.providers.macro_official_v8 import fred_macro_snapshot, nyfed_reference_rates, atlanta_gdpnow
from src.providers.macro import macro_snapshot as market_macro_snapshot
from src.analytics.macro_v8 import macro_scores, sector_macro_fit

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--snapshot",default="web/latest.json")
    a=ap.parse_args()
    p=Path(a.snapshot);snap=json.loads(p.read_text(encoding="utf-8"));s=requests.Session()
    fred=fred_macro_snapshot(session=s)
    ny=nyfed_reference_rates(session=s)
    try:gdp=atlanta_gdpnow(session=s)
    except Exception as e:gdp={"value":None,"error":type(e).__name__,"source":"Atlanta Fed GDPNow"}
    try:market=market_macro_snapshot()
    except Exception as e:market={"error":type(e).__name__}
    regime=macro_scores(fred,ny,gdp,market)
    snap["macro_v8"]={"regime":regime,"fred":fred,"nyfed":ny,"gdpnow":gdp,"market":market}
    for rec in snap.get("tickers",[]):
        rec.setdefault("v8",{})["macro_fit"]=sector_macro_fit(rec.get("sector",""),regime)
    mh=list(snap.get("macro_history_v8",[]))[-179:]
    asof=snap.get("meta",{}).get("as_of")
    point={"date":asof,"regime":regime.get("regime"),"risk":regime.get("macro_risk_score"),**regime.get("axes",{})}
    if not mh or mh[-1].get("date")!=asof:mh.append(point)
    else:mh[-1]=point
    snap["macro_history_v8"]=mh
    snap["meta"]["schema_version"]="8.0"
    snap["sources"]["macro_v8"]={
        "FRED":"St. Louis Fed FRED public CSV series",
        "NYFed":"Federal Reserve Bank of New York reference rates API",
        "GDPNow":"Federal Reserve Bank of Atlanta public GDPNow commentary",
        "Market":"Yahoo Finance via yfinance",
        "note":"Macro scores and sector-fit are transparent local calculations, not vendor ratings."
    }
    p.write_text(json.dumps(snap,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("v8 macro enrichment complete")
if __name__=="__main__":main()
