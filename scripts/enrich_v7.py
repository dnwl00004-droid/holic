
from __future__ import annotations
import argparse,json
from pathlib import Path
from src.providers.prices import download_daily

from src.analytics.ranking_v7 import assign_cross_sectional_ranks
from src.analytics.signal_backtest_v7 import backtest_signals, aggregate_signal_results
from src.analytics.portfolio_risk_v7 import stress_returns

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--snapshot",default="web/latest.json")
    ap.add_argument("--backtest-top",type=int,default=50)
    ap.add_argument("--with-signal-backtest",action="store_true")
    ap.add_argument("--with-stress-library",action="store_true")
    a=ap.parse_args()
    p=Path(a.snapshot);snap=json.loads(p.read_text(encoding="utf-8"))

    # Attach today's changes to each record only during scoring.
    change_map={x["ticker"]:x.get("changes",[]) for x in snap.get("today_changes",[])}
    for r in snap["tickers"]:
        r["_today_changes"]=change_map.get(r["ticker"],[])
    assign_cross_sectional_ranks(snap["tickers"])
    for r in snap["tickers"]:
        r.pop("_today_changes",None)

    if a.with_signal_backtest:
        names=snap["tickers"][:a.backtest_top]
        symbols=[x.get("provider_ticker") or x["ticker"] for x in names]
        price=download_daily(symbols+["SPY"],period="5y")
        bm=price.get("SPY")
        per={}
        if bm is not None:
            for rec in names:
                t=rec.get("provider_ticker") or rec["ticker"]
                if t not in price:continue
                try:
                    bt=backtest_signals(price[t],bm)
                    rec.setdefault("v7",{})["signal_backtest"]=bt
                    per[rec["ticker"]]=bt
                except Exception as e:
                    rec.setdefault("v7",{})["signal_backtest"]={"error":type(e).__name__}
        snap["signal_backtests"]=aggregate_signal_results(per)

        if a.with_stress_library:
            for rec in snap["tickers"]:
                t=rec.get("provider_ticker") or rec["ticker"]
                if t in price:
                    rec.setdefault("v7",{})["stress_returns"]=stress_returns(price[t])

    # Rankings exported separately for faster UI
    snap["revision_rankings"]=sorted([
        {"ticker":r["ticker"],"company":r["company"],"sector":r["sector"],
         "revision_score":r.get("v7",{}).get("revision",{}).get("score"),
         "revision_rank":r.get("v7",{}).get("revision_rank"),
         "change_30d_pct":((r.get("v6") or {}).get("estimates") or {}).get("revision_pulse",{}).get("change_30d_pct"),
         "net_30d":((r.get("v6") or {}).get("estimates") or {}).get("revision_pulse",{}).get("net_30d"),
         "last_surprise_pct":((r.get("v6") or {}).get("estimates") or {}).get("surprise_summary",{}).get("last_surprise_pct"),
         "catalyst_score":r.get("v7",{}).get("catalyst",{}).get("score"),
         "catalyst_rank":r.get("v7",{}).get("catalyst_rank"),
         "expectation_gap":r.get("v7",{}).get("expectation_gap"),
        } for r in snap["tickers"]
        if r.get("v7",{}).get("revision",{}).get("score") is not None
    ],key=lambda x:(x["revision_rank"] or 9999))

    snap["meta"]["schema_version"]="7.0"
    snap["meta"]["v7_ranked_names"]=len(snap["revision_rankings"])
    snap["sources"]["v7_rankings"]={"engine":"revision_score_v1 + catalyst_score_v1","note":"Transparent composite of source metrics"}
    snap["sources"]["signal_backtests"]={"engine":"signal_backtest_v1","provider":"Nasdaq historical quotes","requested_years":5,"note":"Price/volume signals only; cash dividends excluded; actual coverage depends on listing date; current-universe survivorship bias remains"}
    p.write_text(json.dumps(snap,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("v7 enrichment complete")
if __name__=="__main__":main()
