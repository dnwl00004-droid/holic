"""Official schedule parsers with source-specific failures and explicit inferred recurrences."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import re, requests
from lxml import html
from .calendar_v9 import MONTHS, _impact
from ..reliability import now

URLS = {"Federal Reserve":"https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "BLS":"https://www.bls.gov/schedule/news_release/bls.ics", "BEA":"https://www.bea.gov/news/schedule", "EIA":"https://www.eia.gov/petroleum/supply/weekly/schedule.php"}

def event(dt, title, source, time=None, method="official schedule", notes=None):
    importance = "HIGH" if any(x in title.lower() for x in ("consumer price", "employment situation", "personal income", "gdp", "policy decision")) else _impact(title)
    dt_utc = None; dt_kst = None
    if time:
        try:
            time=re.sub(r"a\.?m\.?", "AM", time, flags=re.I);time=re.sub(r"p\.?m\.?", "PM", time, flags=re.I)
            t=datetime.strptime(time.strip(), "%I:%M %p").time() if "M" in time else datetime.strptime(time.strip(), "%H:%M").time()
            est=datetime.combine(dt,t,ZoneInfo("America/New_York"));dt_utc=est.astimezone(timezone.utc).isoformat();dt_kst=est.astimezone(ZoneInfo("Asia/Seoul")).isoformat()
        except ValueError: pass
    return {"date":dt.isoformat(), "time_et":time, "datetime_utc":dt_utc, "datetime_kst":dt_kst, "title":title, "source":source, "url":URLS[source], "method":method,
            "importance":importance, "days_from_today":(dt-datetime.now(ZoneInfo("America/New_York")).date()).days, "category":"Energy" if source=="EIA" else "Central Bank" if source=="Federal Reserve" else "Economic Data", "notes":notes,
            "previous":None,"forecast":None,"actual":None,"surprise":None}

def parse_fomc(text):
    tree=html.fromstring(text); events=[]
    for panel in tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," panel ")]'):
        head=" ".join(panel.xpath('./div[contains(@class,"panel-heading")]//text()'))
        m=re.search(r"(\d{4}) FOMC Meetings",head)
        if not m:continue
        year=int(m.group(1))
        for row in panel.xpath('./div[contains(@class,"fomc-meeting")]'):
            month=" ".join(row.xpath('.//*[contains(@class,"__month")]//text()')).strip()
            dates=" ".join(row.xpath('.//*[contains(@class,"__date")]//text()')).strip()
            parts=re.findall(r"\d{1,2}",dates)
            month=month.split("/")[-1].strip()
            if month not in MONTHS or not parts:continue
            dt=date(year,MONTHS[month],int(parts[-1]));events.append(event(dt,"FOMC Policy Decision","Federal Reserve","14:00",notes="Scheduled decision time; unscheduled actions excluded."))
            minutes=" ".join(row.xpath('.//*[contains(@class,"__minutes")]//text()'))
            mm=re.search(r"Released ([A-Za-z]+) (\d{1,2}), (\d{4})",minutes)
            if mm and mm[1] in MONTHS:events.append(event(date(int(mm[3]),MONTHS[mm[1]],int(mm[2])),"FOMC Minutes","Federal Reserve","14:00"))
    return events

def parse_bls(text):
    text=re.sub(r"\r?\n[ \t]", "", text);events=[]
    for block in text.split("BEGIN:VEVENT")[1:]:
        tm=re.search(r"^DTSTART(?:;[^:]*)?:(\d{8})T(\d{6})",block,re.M);title=re.search(r"^SUMMARY:(.+)",block,re.M)
        if tm and title:
            dt=datetime.strptime(tm[1],"%Y%m%d").date();time=tm[2][:2]+":"+tm[2][2:4]
            events.append(event(dt,title[1].strip().replace("\\,",","),"BLS",time))
    return events

def parse_bea(text):
    tree=html.fromstring(text);events=[]
    # The title identifies the schedule year; never infer a date from the data-reference year.
    headings=" ".join(tree.xpath('//h1//text()|//h2//text()|//caption//text()|//thead//text()'))
    ym=re.search(r"\b(20\d{2})\b",headings);year=int(ym[1]) if ym else date.today().year
    for row in tree.xpath('//tbody/tr'):
        cells=[" ".join(c.xpath('.//text()')).strip() for c in row.xpath('./th|./td')]
        if not cells:continue
        line=" ".join(cells);dm=re.search(r"([A-Za-z]+)\s+(\d{1,2})\s+(\d{1,2}:\d{2}\s*[AP]M)",line,re.I)
        if dm and dm[1] in MONTHS:
            events.append(event(date(year,MONTHS[dm[1]],int(dm[2])),cells[-1],"BEA",dm[3].upper()))
    return events

def parse_eia(text,horizon=120):
    tree=html.fromstring(text);exceptions={};events=[]
    for row in tree.xpath('//tr'):
        cells=[" ".join(c.xpath('.//text()')).strip() for c in row.xpath('./th|./td')]
        if len(cells)<4:continue
        try:
            dt=datetime.strptime(cells[1],"%B %d, %Y").date()
            normal=dt-timedelta(days=(dt.weekday()-2)%7)
            exceptions[normal]=(dt,cells[3])
        except ValueError:continue
    # Recurrence follows the published rule, with the page's holiday exceptions.
    normalized=" ".join(tree.xpath('//text()')).lower()
    if "wednesday" not in normalized or "10:30" not in normalized:raise ValueError("standard_release_rule_not_found")
    d=date.today()
    while d<=date.today()+timedelta(days=horizon):
        if d.weekday()==2:
            actual,time=exceptions.get(d,(d,"10:30"))
            events.append(event(actual,"EIA Petroleum Status Report","EIA",time,method="official recurrence + holiday exception table",notes="Recurring schedule; subject to later changes."))
        d+=timedelta(days=1)
    return events

def official_calendar():
    parsers={"Federal Reserve":parse_fomc,"BLS":parse_bls,"BEA":parse_bea,"EIA":parse_eia}
    def load(item):
        source,url=item
        try:
            r=requests.get(url,timeout=25);r.raise_for_status();rows=parsers[source](r.text)
            if not rows:raise ValueError("no_events_parsed")
            return rows,{"source":source,"status":"ok","last_success":now(),"last_attempt":now(),"count":len(rows)}
        except Exception as e:return [],{"source":source,"status":"unavailable","error":type(e).__name__,"last_attempt":now()}
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(load,URLS.items()))
    all_rows=[e for rows,_ in results for e in rows];today=date.today();cutoff=today+timedelta(days=120)
    rows=sorted({(e["date"],e["title"],e["source"]):e for e in all_rows if today-timedelta(days=1)<=date.fromisoformat(e["date"])<=cutoff}.values(),key=lambda e:(e["date"],e.get("time_et") or ""))
    return {"events":rows,"archive_events":all_rows,"providers":[h for _,h in results]+[{"source":"OPEC / Treasury / ISM / Jobless Claims","status":"unavailable","error":"schedule adapter not yet verified"}],
            "high_impact_next_7d":sum(e["importance"]=="HIGH" and 0<=e["days_from_today"]<=7 for e in rows),"high_impact_next_30d":sum(e["importance"]=="HIGH" and 0<=e["days_from_today"]<=30 for e in rows),"generated":now(),
            "notes":["ET and KST use timezone-aware daylight-saving conversion.","Forecast / actual / surprise remain null without a verified release provider."]}
