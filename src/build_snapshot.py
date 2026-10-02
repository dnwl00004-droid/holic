
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import requests

from .providers.universe import load_sp500
from .providers.yahoo import download_daily
from .providers.sec import ticker_to_cik_map, cached_company_facts, quarterly_growth_snapshot
from .analytics.rs import weighted_momentum, relative_line_change, percentile_1_99, quadrant
from .analytics.trend import trend_template
from .analytics.stage import stage_proxy
from .analytics.patterns import vcp_proxy, double_bottom_proxy
from .analytics.market import distribution_pressure, regime
from .analytics.composite import score as composite_score
from .analytics.dual_score import strength_score, setup_score, radar_axes, status_label
from .analytics.signals import load_log, save_log, update_signal_log, scorecard, today_changes
from .analytics.factors import period_returns, risk_metrics, warning_flags, assign_sector_factor_grades
from .analytics.breadth_plus import market_breadth_plus, market_quality_score
from .analytics.technicals_plus import rsi14, divergence_proxy, exhaustion_9_proxy, volume_breakthrough, entry_timing_score
from .analytics.screeners_plus import rs_new_high_signal, multi_screeners, group_rankings

def safe_float(x):
    try:
        x=float(x); return x if np.isfinite(x) else None
    except Exception:return None

def read_json(path):
    p=Path(path)
    if not p.exists():return None
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None

def enrich_sec(records, with_sec=False):
    if not with_sec:return
    try:
        session=requests.Session()
        cikmap=ticker_to_cik_map(session)
    except Exception:
        return
    for rec in records:
        ticker=rec["ticker"].replace(".","-").upper()
        cik=cikmap.get(ticker) or cikmap.get(rec["ticker"].upper())
        if not cik:continue
        try:
            facts=cached_company_facts(ticker,cik,session=session)
            g=quarterly_growth_snapshot(facts)
            rec["earnings"].update(g)
            rec["earnings"]["source"]="SEC EDGAR CompanyFacts"
        except Exception as e:
            rec["earnings"]["sec_error"]=type(e).__name__

def build(output_path="web/latest.json", signal_log_path="data/output/signal_log.json", with_sec=False):
    benchmark=download_daily(["SPY"],period="3y")
    spy=benchmark.get("SPY")
    if spy is None or spy.empty:raise RuntimeError("SPY benchmark data unavailable")
    uni=load_sp500(); provider=uni["provider_ticker"].tolist()
    prices={"SPY":spy}
    for i in range(0,len(provider),50):prices.update(download_daily(provider[i:i+50],period="3y"))
    if sum(t in prices and len(prices[t])>=260 for t in provider)<len(provider)*.90:
        raise RuntimeError("Less than 90% universe price coverage; retain previous snapshot")

    raw_mom={t:weighted_momentum(prices[t]["close"]) if t in prices else None for t in provider}
    raw_short={t:relative_line_change(prices[t]["close"],spy["close"]) if t in prices else None for t in provider}
    rs_scores=percentile_1_99(raw_mom); short_scores=percentile_1_99(raw_short)

    pmap={t:prices[t] for t in provider if t in prices}
    breadth=market_breadth_plus(pmap,spy)
    dist=distribution_pressure(spy)
    mregime=regime(spy,breadth.get("above_200"),dist.get("count"))
    mquality=market_quality_score(breadth,spy)

    previous=read_json(output_path)
    prev_by={x["ticker"]:x for x in (previous or {}).get("tickers",[])}
    meta_by=uni.set_index("provider_ticker").to_dict("index")
    records=[]

    for t in provider:
        if t not in prices or len(prices[t])<260:continue
        df=prices[t]; meta=meta_by[t]
        rs=rs_scores.get(t); srs=short_scores.get(t)
        trend=trend_template(df,rs); stage=stage_proxy(df)
        vcp=vcp_proxy(df); db=double_bottom_proxy(df)
        close=float(df["close"].iloc[-1]); prev=float(df["close"].iloc[-2]); chg=(close/prev-1)*100
        earnings={"eps_growth_yoy":None,"revenue_growth_yoy":None,"source":"not enriched"}
        strength=strength_score(rs,srs,trend,stage)
        setup=setup_score(vcp,db)
        radar=radar_axes(rs,trend,vcp,earnings)
        status=status_label(strength,setup,vcp)
        periods=period_returns(df["close"]); risk=risk_metrics(df)
        vbreak=volume_breakthrough(df)
        rsnh=rs_new_high_signal(df["close"],spy["close"])
        entry=entry_timing_score(df,vcp)
        tech={"rsi14":rsi14(df["close"]),"divergence":divergence_proxy(df),"exhaustion9":exhaustion_9_proxy(df["close"]),
              "volume_breakthrough":vbreak}
        chartdf=df.dropna(subset=["close"]).tail(120)

        rec={
          "ticker":meta["ticker"],"provider_ticker":t,"company":meta["company"],"sector":meta["sector"],"industry":meta["industry"],
          "price":{"close":round(close,4),"change_pct":round(chg,3),"as_of":str(df.index[-1].date()),"source":"Yahoo Finance / yfinance","method":"adjusted daily OHLCV",
                   "sma50":round(float(df["close"].rolling(50).mean().iloc[-1]),4),
                   "sma150":round(float(df["close"].rolling(150).mean().iloc[-1]),4),
                   "sma200":round(float(df["close"].rolling(200).mean().iloc[-1]),4)},
          "rs":{"score":rs,"short":srs,"quadrant":quadrant(rs,srs),"raw_momentum":safe_float(raw_mom.get(t)),
                "rs_line_change_21d":safe_float(raw_short.get(t)),**rsnh},
          "trend_template":trend,"stage":stage,
          "patterns":{"primary":"VCP" if vcp.get("detected") else ("Double Bottom" if db.get("detected") else None),
                      "vcp":vcp,"double_bottom":db},
          "earnings":earnings,"period_returns":periods,"risk":risk,"technicals":tech,"entry":entry,
          "scores":{"strength":strength,"setup":setup,"entry":entry.get("score"),
                    "composite":composite_score(rs,srs,trend,vcp,None),"radar":radar,"status":status},
          "spark":[round(float(v),4) for v in chartdf["close"].tail(28)],
          "chart":[{"d":idx.strftime("%Y-%m-%d"),"c":round(float(row["close"]),4),
                    "v":int(row["volume"]) if "volume" in row and not np.isnan(row["volume"]) else None}
                   for idx,row in chartdf.iterrows()]
        }
        rec["warnings"]=warning_flags(rec)
        rec["screeners"]=multi_screeners(rec,vbreak,rsnh)

        ph=list(prev_by.get(meta["ticker"],{}).get("score_history",[]))[-29:]
        point={"date":str(df.index[-1].date()),"strength":strength,"setup":setup,"entry":entry.get("score"),"rs":rs,"short_rs":srs}
        if not ph or ph[-1].get("date")!=point["date"]:ph.append(point)
        else:ph[-1]=point
        rec["score_history"]=ph
        records.append(rec)

    # Optional SEC enrichment; recompute growth-sensitive pieces afterwards
    enrich_sec(records,with_sec=with_sec)
    for rec in records:
        rec["scores"]["radar"]=radar_axes(rec["rs"]["score"],rec["trend_template"],rec["patterns"]["vcp"],rec["earnings"])
        rec["screeners"]=multi_screeners(rec,rec["technicals"]["volume_breakthrough"],
                                          {"rs_new_high":rec["rs"].get("rs_new_high"),"before_price":rec["rs"].get("before_price")})

    assign_sector_factor_grades(records)
    groups=group_rankings(records)

    # Add rank-change against previous group snapshot
    prev_groups={g["group"]:g for g in (previous or {}).get("groups",[])}
    for g in groups:
        old=prev_groups.get(g["group"],{}).get("rank")
        g["rank_change"]=None if old is None else old-g["rank"]

    records.sort(key=lambda x:(x["scores"]["strength"]+(x["scores"].get("entry") or 0)+x["scores"]["setup"]),reverse=True)
    as_of=str(spy.index[-1].date())
    changes=today_changes(previous,records)
    log=load_log(signal_log_path); log=update_signal_log(log,records,prices,as_of); save_log(signal_log_path,log)

    # rolling market history
    mh=list((previous or {}).get("market_history",[]))[-59:]
    mh_point={"date":as_of,"quality":mquality.get("score"),"above50":breadth.get("above_50"),
              "above200":breadth.get("above_200"),"ad_ratio":breadth.get("ad_ratio"),
              "up4":breadth.get("up_4pct"),"down4":breadth.get("down_4pct")}
    if not mh or mh[-1].get("date")!=as_of:mh.append(mh_point)
    else:mh[-1]=mh_point

    return {
      "meta":{"schema_version":"4.0","generated_at":datetime.now(timezone.utc).isoformat(),"as_of":as_of,
              "universe":"S&P 500 prototype universe","universe_count":len(records),"demo":False,
              "fundamentals_enriched":bool(with_sec)},
      "sources":{"price":{"provider":"Yahoo Finance","adapter":"yfinance","type":"adjusted daily OHLCV"},
                 "fundamentals":{"provider":"SEC EDGAR CompanyFacts","enabled":bool(with_sec)},
                 "benchmark":{"symbol":"SPY","provider":"Yahoo Finance"},
                 "universe":{"provider":"Wikipedia S&P 500 table","use":"prototype constituent metadata"}},
      "methodology":{"rs_score":"40% 63d + 20% 126d + 20% 189d + 20% 252d, percentile-ranked",
                     "short_rs":"21d stock/SPY relative-line change, percentile-ranked",
                     "strength":"structural leadership","setup":"pattern/setup quality","entry":"current timing quality",
                     "breadth":"cross-sectional OHLCV participation metrics"},
      "market":{"regime":mregime,"quality":mquality,"breadth":breadth,
                "distribution_count":dist.get("count"),"setup_count":sum(bool(x["patterns"]["primary"]) for x in records)},
      "market_history":mh,"groups":groups,"today_changes":changes,
      "signal_scorecard":scorecard(log),
      "signals_recent":sorted(log,key=lambda x:x.get("signal_date",""),reverse=True)[:50],
      "tickers":records
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="web/latest.json")
    ap.add_argument("--signal-log",default="data/output/signal_log.json")
    ap.add_argument("--with-sec",action="store_true")
    a=ap.parse_args()
    snap=build(a.output,a.signal_log,a.with_sec)
    p=Path(a.output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(snap,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(f"Wrote {p} with {len(snap['tickers'])} symbols")

if __name__=="__main__":main()
