
from __future__ import annotations
import argparse,json
from pathlib import Path
from src.providers.prices import download_daily

from src.providers.yahoo_estimates import estimate_snapshot
from src.analytics.valuation_v6 import reverse_dcf_implied_growth, dcf_sensitivity
from src.analytics.replay_v6 import backtest_price_signal
from src.analytics.catalyst_v6 import build_catalyst_timeline

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--snapshot",default="web/latest.json")
    ap.add_argument("--top",type=int,default=80)
    ap.add_argument("--with-replay",action="store_true")
    ap.add_argument("--with-estimates",action="store_true")
    a=ap.parse_args()
    p=Path(a.snapshot);snap=json.loads(p.read_text(encoding="utf-8"))
    top=snap["tickers"][:a.top]
    symbols=[x.get("provider_ticker") or x["ticker"] for x in top]
    spy=None
    price_map={}
    if a.with_replay:
        price_map=download_daily(symbols+["SPY"],period="3y")
        spy=price_map.get("SPY")

    for rec in top:
        rec.setdefault("v6",{})
        t=rec.get("provider_ticker") or rec["ticker"]
        try: est=estimate_snapshot(t) if a.with_estimates else {"status":"unavailable","error":"analyst_estimate_feed_not_connected"}
        except Exception as e: est={"error":type(e).__name__}
        rec["v6"]["estimates"]=est

        fq=(rec.get("v5") or {}).get("fundamental_quality") or {}
        base=fq.get("base") or {}
        margins=fq.get("margins") or {}
        mc=est.get("market_cap")
        shares=est.get("shares_outstanding")
        rev=base.get("revenue"); net_debt=base.get("net_debt"); fcfm=margins.get("fcf_margin_pct")
        rdcf=reverse_dcf_implied_growth(mc,net_debt,rev,fcfm)
        if rdcf.get("available"):
            rdcf["sensitivity"]=dcf_sensitivity(rev,fcfm,net_debt,shares) if shares else {"available":False}
        rec["v6"]["reverse_dcf"]=rdcf

        if a.with_replay and spy is not None and t in price_map:
            try:rec["v6"]["replay"]=backtest_price_signal(price_map[t],spy)
            except Exception as e:rec["v6"]["replay"]={"error":type(e).__name__}

        rec["v6"]["catalysts"]=build_catalyst_timeline(rec,snap.get("today_changes"))

    snap["meta"]["schema_version"]="6.0"
    snap["meta"]["v6_enriched_top_n"]=len(top)
    snap["sources"]["estimates"]={"provider":"Yahoo Finance via yfinance","enabled":a.with_estimates,"status":"unavailable" if not a.with_estimates else "attempted","fields":"EPS trend/revisions, earnings history, market cap"}
    snap["sources"]["valuation"]={"engine":"reverse_dcf_constant_margin_v1","note":"Model output, not vendor data"}
    snap["sources"]["replay"]={"engine":"price_only_replay_v1","provider":"Nasdaq historical quotes","caveat":"Price returns exclude cash dividends; current-universe survivorship bias"}
    p.write_text(json.dumps(snap,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(f"v6 enrichment complete for {len(top)} names")
if __name__=="__main__":main()
