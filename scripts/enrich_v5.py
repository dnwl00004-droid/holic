
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from datetime import datetime,timedelta
import requests

from src.providers.sec import ticker_to_cik_map,cached_company_facts
from src.analytics.fundamentals_plus import quality_snapshot
from src.providers.sec_activity import insider_activity
from src.providers.finra import query_daily_short_volume,summarize_short_volume
from src.providers.macro import macro_snapshot

def read(path,default):
    p=Path(path)
    if not p.exists():return default
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return default

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--snapshot",default="web/latest.json")
    ap.add_argument("--top",type=int,default=80,help="enrich top N candidates for network-heavy SEC Form 4 calls")
    ap.add_argument("--with-finra",action="store_true")
    ap.add_argument("--with-macro",action="store_true")
    a=ap.parse_args()

    p=Path(a.snapshot);snap=json.loads(p.read_text(encoding="utf-8"))
    session=requests.Session()
    cikmap=ticker_to_cik_map(session)
    inst=read("data/output/institutional13f.json",{}).get("tickers",{})

    # top candidates: network-heavy activity calls only here; fundamentals use existing SEC cache
    ranked=snap["tickers"][:a.top]
    for rec in snap["tickers"]:
        t=rec["ticker"].upper(); cik=cikmap.get(t)
        rec.setdefault("v5",{})
        rec["v5"]["institutional_13f"]=inst.get(t)
        if cik:
            try:
                facts=cached_company_facts(t,cik,session=session)
                rec["v5"]["fundamental_quality"]=quality_snapshot(facts,market_cap=None,price=rec["price"]["close"])
            except Exception as e:
                rec["v5"]["fundamental_quality"]={"error":type(e).__name__}
    for rec in ranked:
        t=rec["ticker"].upper();cik=cikmap.get(t)
        if not cik:continue
        try:rec["v5"]["insider"]=insider_activity(cik,session=session)
        except Exception as e:rec["v5"]["insider"]={"error":type(e).__name__}

    if a.with_finra:
        end=datetime.utcnow().date();start=end-timedelta(days=35)
        try:
            rows=query_daily_short_volume([x["ticker"] for x in ranked],start.isoformat(),end.isoformat(),session=session)
            short=summarize_short_volume(rows)
        except Exception as e:
            short={"_error":{"error":type(e).__name__}}
        for rec in ranked:rec["v5"]["short_volume"]=short.get(rec["ticker"])

    if a.with_macro:
        try:snap["macro"]=macro_snapshot()
        except Exception as e:snap["macro"]={"error":type(e).__name__}

    snap["meta"]["schema_version"]="5.0"
    snap["meta"]["v5_enriched_top_n"]=len(ranked)
    snap["sources"]["insider"]={"provider":"SEC Form 4","scope":"open-market P/S transactions"}
    snap["sources"]["institutional"]={"provider":"SEC 13F","mapping":"conservative issuer-name mapping"}
    snap["sources"]["short_volume"]={"provider":"FINRA","caveat":"short sale volume != short interest"}
    p.write_text(json.dumps(snap,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("v5 enrichment complete")
if __name__=="__main__":main()
