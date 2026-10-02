
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, re, time
import requests
import xml.etree.ElementTree as ET

SEC_SUBMISSIONS="https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVE="https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{primary_doc}"

HEADERS={"User-Agent":"RS-Radar research contact@example.com","Accept-Encoding":"gzip, deflate"}

def _cache_get_json(url, cache_file:Path, max_age_hours=24, session=None):
    if cache_file.exists():
        age=datetime.now(timezone.utc)-datetime.fromtimestamp(cache_file.stat().st_mtime,tz=timezone.utc)
        if age<timedelta(hours=max_age_hours):
            try:return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:pass
    s=session or requests.Session()
    r=s.get(url,headers=HEADERS,timeout=30);r.raise_for_status()
    data=r.json();cache_file.parent.mkdir(parents=True,exist_ok=True)
    cache_file.write_text(json.dumps(data,separators=(",",":")),encoding="utf-8")
    return data

def recent_form4_filings(cik:str, cache_dir="data/cache/sec_submissions", days=120, limit=20, session=None):
    p=Path(cache_dir)/f"{cik}.json"
    data=_cache_get_json(SEC_SUBMISSIONS.format(cik=cik.zfill(10)),p,24,session)
    recent=data.get("filings",{}).get("recent",{})
    forms=recent.get("form",[]); acc=recent.get("accessionNumber",[]); docs=recent.get("primaryDocument",[]); dates=recent.get("filingDate",[])
    cutoff=datetime.now(timezone.utc).date()-timedelta(days=days)
    out=[]
    for form,a,doc,dt in zip(forms,acc,docs,dates):
        if form not in {"4","4/A"}:continue
        try:
            if datetime.fromisoformat(dt).date()<cutoff:continue
        except Exception:pass
        out.append({"form":form,"accession":a,"primary_doc":doc,"filing_date":dt})
        if len(out)>=limit:break
    return out

def _text(el,path):
    z=el.find(path)
    return None if z is None else (z.text or "").strip()

def parse_form4_xml(xml_text:str)->dict:
    root=ET.fromstring(xml_text)
    owner=_text(root,"./reportingOwner/reportingOwnerId/rptOwnerName")
    relation={
        "director":_text(root,"./reportingOwner/reportingOwnerRelationship/isDirector"),
        "officer":_text(root,"./reportingOwner/reportingOwnerRelationship/isOfficer"),
        "ten_percent_owner":_text(root,"./reportingOwner/reportingOwnerRelationship/isTenPercentOwner"),
        "officer_title":_text(root,"./reportingOwner/reportingOwnerRelationship/officerTitle"),
    }
    tx=[]
    for node in root.findall("./nonDerivativeTable/nonDerivativeTransaction"):
        code=_text(node,"./transactionCoding/transactionCode")
        shares=_text(node,"./transactionAmounts/transactionShares/value")
        ad=_text(node,"./transactionAmounts/transactionAcquiredDisposedCode/value")
        price=_text(node,"./transactionAmounts/transactionPricePerShare/value")
        date=_text(node,"./transactionDate/value")
        try:shares=float(shares) if shares else None
        except:shares=None
        try:price=float(price) if price else None
        except:price=None
        tx.append({"code":code,"shares":shares,"acquired_disposed":ad,"price":price,"date":date,
                   "value":round(shares*price,2) if shares is not None and price is not None else None})
    return {"owner":owner,"relationship":relation,"transactions":tx}

def insider_activity(cik:str, cache_dir="data/cache/form4", days=120, session=None)->dict:
    s=session or requests.Session()
    filings=recent_form4_filings(cik,days=days,session=s)
    rows=[]
    for f in filings:
        acc=f["accession"].replace("-","")
        url=SEC_ARCHIVE.format(cik_int=int(cik),accession_nodash=acc,primary_doc=f["primary_doc"])
        cp=Path(cache_dir)/str(cik)/f"{acc}.xml"
        if cp.exists():
            text=cp.read_text(encoding="utf-8",errors="ignore")
        else:
            try:
                r=s.get(url,headers=HEADERS,timeout=30);r.raise_for_status();text=r.text
                cp.parent.mkdir(parents=True,exist_ok=True);cp.write_text(text,encoding="utf-8")
                time.sleep(.12)
            except Exception:continue
        try:
            parsed=parse_form4_xml(text)
            for tx in parsed["transactions"]:
                if tx.get("code") not in {"P","S"}:continue # open-market purchase/sale focus
                rows.append({**tx,"owner":parsed["owner"],"relationship":parsed["relationship"],"filing_date":f["filing_date"]})
        except Exception:continue
    buys=[x for x in rows if x.get("code")=="P"]; sells=[x for x in rows if x.get("code")=="S"]
    val=lambda xs:sum(x.get("value") or 0 for x in xs)
    return {"lookback_days":days,"purchase_count":len(buys),"sale_count":len(sells),
            "purchase_value":round(val(buys),2),"sale_value":round(val(sells),2),
            "net_open_market_value":round(val(buys)-val(sells),2),
            "recent":sorted(rows,key=lambda x:(x.get("date") or "",x.get("filing_date") or ""),reverse=True)[:12],
            "source":"SEC Form 4","note":"Open-market P/S transactions only; grants/exercises excluded"}
