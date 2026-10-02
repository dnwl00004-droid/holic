from __future__ import annotations
from datetime import date, datetime, timedelta
from urllib.parse import urljoin
import re
from io import StringIO
import requests
import pandas as pd
from lxml import html, etree

HEADERS={"User-Agent":"RS-Radar macro calendar research"}
MONTHS={m:i for i,m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"],1)}

IMPORTANCE={
    "FOMC":"HIGH","CPI":"HIGH","Employment Situation":"HIGH","Personal Income and Outlays":"HIGH","GDP":"HIGH",
    "PPI":"MEDIUM","JOLTS":"MEDIUM","ECI":"MEDIUM","EIA Petroleum":"MEDIUM","Treasury Auction":"MEDIUM",
    "OPEC":"HIGH","Trade":"MEDIUM",
}

def _impact(title):
    for k,v in IMPORTANCE.items():
        if k.lower() in title.lower():return v
    return "LOW"

def _event(dt,title,source,category,time_et=None,url=None,notes=None):
    today=date.today(); d=(dt-today).days
    return {"date":dt.isoformat(),"time_et":time_et,"title":title,"category":category,"importance":_impact(title),
            "days_from_today":d,"source":source,"url":url,"notes":notes}


def fomc_events(year=None,session=None,include_past=False):
    year=year or date.today().year; s=session or requests.Session()
    url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    r=s.get(url,headers=HEADERS,timeout=30);r.raise_for_status()
    txt="\n".join(x.strip() for x in html.fromstring(r.text).xpath("//text()") if x.strip())
    # Restrict roughly to requested year block.
    pos=txt.find(f"{year} FOMC Meetings"); block=txt[pos:pos+5000] if pos>=0 else txt
    events=[]
    for month,mi in MONTHS.items():
        # Month followed soon by '27-28*' or '28-29'
        for m in re.finditer(rf"\b{month}\b[\s\S]{{0,100}}?\b(\d{{1,2}})(?:-(\d{{1,2}}))?\*?",block):
            d2=int(m.group(2) or m.group(1))
            try:dt=date(year,mi,d2)
            except:continue
            if include_past or dt>=date.today()-timedelta(days=7):
                events.append(_event(dt,"FOMC Policy Decision","Federal Reserve","Central Bank","14:00",url,"Decision time is normally 2:00 PM ET; press conference follows when scheduled."))
            break
    # de-dupe
    return list({(x["date"],x["title"]):x for x in events}.values())


def bls_events(year=None,session=None):
    year=year or date.today().year;url=f"https://www.bls.gov/schedule/{year}/";events=[]
    try:
        tables=pd.read_html(url)
        for df in tables:
            for _,row in df.iterrows():
                vals=[str(x) for x in row.tolist()]
                line=" | ".join(vals)
                dm=re.search(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})",line)
                if not dm:continue
                title=next((v for v in vals if any(k in v for k in ["Consumer Price Index","Employment Situation","Producer Price Index","Job Openings","Employment Cost Index","Import and Export Price"])),None)
                if not title:continue
                dt=date(int(dm.group(4)),MONTHS[dm.group(2)],int(dm.group(3)))
                tm=re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))",line,re.I)
                events.append(_event(dt,title,"BLS","Economic Data",tm.group(1) if tm else None,url))
    except Exception:pass
    return events


def bea_events(year=None,session=None):
    year=year or date.today().year;url="https://www.bea.gov/news/schedule";events=[]
    try:
        tables=pd.read_html(url)
        for df in tables:
            for _,row in df.iterrows():
                line=" | ".join(str(x) for x in row.tolist())
                dm=re.search(r"([A-Za-z]+)\s+(\d{1,2})\s+(\d{1,2}:\d{2}\s*[AP]M)",line,re.I)
                if not dm or dm.group(1) not in MONTHS:continue
                title=None
                for key in ["Gross Domestic Product","GDP","Personal Income and Outlays","International Trade in Goods and Services"]:
                    if key.lower() in line.lower():title=key;break
                if not title:continue
                dt=date(year,MONTHS[dm.group(1)],int(dm.group(2)))
                events.append(_event(dt,title,"BEA","Economic Data",dm.group(3).upper(),url))
    except Exception:pass
    return events


def eia_events(horizon_days=70):
    url="https://www.eia.gov/petroleum/supply/weekly/schedule.php";today=date.today();events=[]
    # Standard Wednesday schedule. Official page notes holiday exceptions; we attach warning.
    d=today
    while d<=today+timedelta(days=horizon_days):
        if d.weekday()==2:
            events.append(_event(d,"EIA Petroleum Status Report","EIA","Energy","10:30",url,"Usually Wednesday 10:30 AM ET; holiday weeks can shift."))
        d+=timedelta(days=1)
    return events


def treasury_auction_events(session=None):
    s=session or requests.Session();page="https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding/most-recent-quarterly-refunding-documents/"
    events=[]
    try:
        r=s.get(page,headers=HEADERS,timeout=30);r.raise_for_status();tree=html.fromstring(r.text)
        href=next((h for h in tree.xpath("//a/@href") if "TentativeAuctionSchedule" in h and h.lower().endswith(".xml")),None)
        if not href:return events
        url=urljoin(page,href);rx=s.get(url,headers=HEADERS,timeout=30);rx.raise_for_status();root=etree.fromstring(rx.content)
        # Generic parse: inspect leaf text for announcement/auction date plus security term.
        for node in root.xpath("//*[not(*)]"):
            text=(node.text or "").strip()
            if not re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}",text):continue
            dt=datetime.strptime(text,"%m/%d/%Y").date()
            if dt<date.today()-timedelta(days=2):continue
            parent=node.getparent();blob=" ".join(t.strip() for t in parent.itertext() if t.strip())
            term=re.search(r"\b(\d+[- ]?(?:Week|Month|Year)|TIPS|FRN)\b",blob,re.I)
            title=f"Treasury Auction {term.group(1) if term else ''}".strip()
            events.append(_event(dt,title,"U.S. Treasury","Treasury Supply",None,url,"Tentative quarterly auction schedule."))
    except Exception:pass
    # Excessively generic XMLs can produce duplicates; keep unique date/title.
    return list({(x["date"],x["title"]):x for x in events}.values())[:80]


def opec_events_2026():
    # Current official dates verified 2026-09-29. Kept explicit because OPEC meeting timing is changed by press release.
    rows=[
      (date(2026,10,4),"OPEC+ voluntary-adjustment countries meeting","https://www.opec.org/pr-detail/613-6-september-2026.html","Monthly review of market conditions and production policy."),
      (date(2026,10,4),"68th JMMC Meeting","https://www.opec.org/pr-detail/612-2-august-2026.html","Joint Ministerial Monitoring Committee."),
      (date(2026,11,29),"42nd OPEC and non-OPEC Ministerial Meeting","https://www.opec.org/pr-detail/605-7-june-2026.html","Ministerial meeting."),
    ]
    return [_event(d,t,"OPEC","Energy Policy",None,u,n) for d,t,u,n in rows if d>=date.today()-timedelta(days=7)]


def macro_calendar_snapshot(horizon_days=120):
    all_events=[]
    for fn in [fomc_events,bls_events,bea_events,treasury_auction_events]:
        try:all_events.extend(fn())
        except Exception:pass
    all_events.extend(eia_events(horizon_days))
    if date.today().year==2026:all_events.extend(opec_events_2026())
    cutoff=date.today()+timedelta(days=horizon_days)
    rows=[x for x in all_events if date.fromisoformat(x["date"])<=cutoff and date.fromisoformat(x["date"])>=date.today()-timedelta(days=1)]
    rows=sorted({(x["date"],x["title"]):x for x in rows}.values(),key=lambda x:(x["date"],x.get("time_et") or ""))
    high7=sum(x["importance"]=="HIGH" and 0<=x["days_from_today"]<=7 for x in rows)
    high30=sum(x["importance"]=="HIGH" and 0<=x["days_from_today"]<=30 for x in rows)
    return {"events":rows,"high_impact_next_7d":high7,"high_impact_next_30d":high30,"generated":datetime.now().isoformat(),
            "notes":["Times are Eastern Time when shown.","EIA holiday weeks may shift from the normal Wednesday release.","OPEC dates are updated from official press releases."]}
