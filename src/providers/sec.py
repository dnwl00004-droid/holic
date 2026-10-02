
from __future__ import annotations
import requests
import os

SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

DEFAULT_HEADERS = {
    # Replace with a real contact in production. SEC asks automated clients to identify themselves.
    "User-Agent": os.environ.get("SEC_USER_AGENT", "RS-Radar research (contact not configured)"),
    "Accept-Encoding": "gzip, deflate",
}

REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "Revenues",
]
EPS_TAGS = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
NET_INCOME_TAGS = ["NetIncomeLoss"]

def ticker_to_cik_map(session: requests.Session | None = None) -> dict[str, str]:
    s = session or requests.Session()
    r = s.get(SEC_TICKERS, headers=DEFAULT_HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return {
        row["ticker"].upper(): str(row["cik_str"]).zfill(10)
        for row in data.values()
    }

def company_facts(cik: str, session: requests.Session | None = None) -> dict:
    s = session or requests.Session()
    r = s.get(SEC_FACTS.format(cik=cik.zfill(10)), headers=DEFAULT_HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def _recent_quarters_from_tag(facts: dict, tags: list[str], unit_candidates: list[str], n=8):
    usgaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        node = usgaap.get(tag, {})
        units = node.get("units", {})
        for unit in unit_candidates:
            vals = units.get(unit, [])
            rows = []
            for x in vals:
                if x.get("form") not in {"10-Q", "10-K"}:
                    continue
                if not x.get("end") or x.get("val") is None:
                    continue
                rows.append({
                    "end": x.get("end"),
                    "fy": x.get("fy"),
                    "fp": x.get("fp"),
                    "form": x.get("form"),
                    "filed": x.get("filed"),
                    "value": x.get("val"),
                    "tag": tag,
                    "unit": unit,
                })
            # de-dupe by end date; prefer latest filed observation
            by_end = {}
            for r in sorted(rows, key=lambda z: (z["end"], z["filed"] or "")):
                by_end[r["end"]] = r
            out = sorted(by_end.values(), key=lambda z: z["end"], reverse=True)
            if out:
                return out[:n]
    return []

def extract_financials(facts: dict) -> dict:
    return {
        "revenue": _recent_quarters_from_tag(facts, REVENUE_TAGS, ["USD"]),
        "eps": _recent_quarters_from_tag(facts, EPS_TAGS, ["USD/shares", "USD / shares"]),
        "net_income": _recent_quarters_from_tag(facts, NET_INCOME_TAGS, ["USD"]),
    }


# ---- v4 cached enrichment helpers ----
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, time, re

def cached_company_facts(ticker: str, cik: str, cache_dir="data/cache/sec", max_age_days=7,
                         session=None, sleep_seconds=.12) -> dict:
    p=Path(cache_dir); p.mkdir(parents=True,exist_ok=True)
    f=p/f"{ticker.upper().replace('.','-')}.json"
    if f.exists():
        age=datetime.now(timezone.utc)-datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if age < timedelta(days=max_age_days):
            try:return json.loads(f.read_text(encoding="utf-8"))
            except Exception:pass
    data=company_facts(cik,session=session)
    f.write_text(json.dumps(data,separators=(",",":")),encoding="utf-8")
    time.sleep(sleep_seconds)
    return data

def _quarter_frames(facts: dict, tags: list[str], unit_candidates: list[str]):
    usgaap=facts.get("facts",{}).get("us-gaap",{})
    for tag in tags:
        units=usgaap.get(tag,{}).get("units",{})
        for unit in unit_candidates:
            vals=units.get(unit,[])
            rows=[]
            for x in vals:
                frame=x.get("frame") or ""
                if not re.match(r"CY\d{4}Q[1-4]$",frame): continue
                if x.get("val") is None: continue
                rows.append({"frame":frame,"value":x["val"],"end":x.get("end"),"filed":x.get("filed"),"tag":tag})
            if rows:
                by={}
                for r in sorted(rows,key=lambda z:(z["frame"],z.get("filed") or "")):by[r["frame"]]=r
                return sorted(by.values(),key=lambda z:z["frame"])
    return []

def quarterly_growth_snapshot(facts: dict) -> dict:
    rev=_quarter_frames(facts,REVENUE_TAGS,["USD"])
    eps=_quarter_frames(facts,EPS_TAGS,["USD/shares","USD / shares"])
    def yoy(rows):
        if len(rows)<5:return None
        latest=rows[-1]
        year=int(latest["frame"][2:6]); q=latest["frame"][-2:]
        target=f"CY{year-1}{q}"
        prev=next((r for r in rows if r["frame"]==target),None)
        if not prev or prev["value"] in (0,None):return None
        return round((float(latest["value"])/float(prev["value"])-1)*100,2)
    return {
        "revenue_growth_yoy":yoy(rev),
        "eps_growth_yoy":yoy(eps),
        "latest_revenue_frame":rev[-1]["frame"] if rev else None,
        "latest_eps_frame":eps[-1]["frame"] if eps else None,
    }
