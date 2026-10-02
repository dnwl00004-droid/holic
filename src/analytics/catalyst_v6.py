
from __future__ import annotations

def build_catalyst_timeline(rec:dict, today_changes:list|None=None):
    items=[]
    t=rec["ticker"]
    # Earnings / revisions
    ya=(rec.get("v6") or {}).get("estimates") or {}
    if ya.get("next_earnings"):
        items.append({"type":"earnings","date":str(ya["next_earnings"]),"title":"Next earnings","detail":"Scheduled/estimated earnings date from Yahoo"})
    rp=ya.get("revision_pulse") or {}
    if rp.get("change_30d_pct") is not None:
        direction="positive" if rp["change_30d_pct"]>0 else "negative" if rp["change_30d_pct"]<0 else "neutral"
        items.append({"type":"revision","date":None,"title":"EPS revision pulse",
                      "detail":f"30D estimate change {rp['change_30d_pct']}% · net revisions {rp.get('net_30d')}",
                      "direction":direction})
    ss=ya.get("surprise_summary") or {}
    if ss.get("last_surprise_pct") is not None:
        items.append({"type":"surprise","date":None,"title":"Latest earnings surprise",
                      "detail":f"{ss['last_surprise_pct']}% vs estimate",
                      "direction":"positive" if ss["last_surprise_pct"]>0 else "negative"})

    # Insider
    ins=(rec.get("v5") or {}).get("insider") or {}
    for x in (ins.get("recent") or [])[:5]:
        code=x.get("code")
        items.append({"type":"insider","date":x.get("date") or x.get("filing_date"),
                      "title":"Open-market insider purchase" if code=="P" else "Open-market insider sale",
                      "detail":f"{x.get('owner') or 'Insider'} · value {x.get('value') or 'n/a'}",
                      "direction":"positive" if code=="P" else "negative"})

    # Technical changes
    for ch in today_changes or []:
        if ch.get("ticker")==t:
            for text in ch.get("changes",[]):
                items.append({"type":"technical","date":None,"title":"Technical change","detail":text,"direction":"neutral"})

    # Optional AI filings already attached by another job
    ai=(rec.get("v6") or {}).get("ai_events") or []
    for e in ai[:5]:
        items.append({"type":"filing_ai","date":e.get("filing_date"),"title":e.get("summary","Filing event"),
                      "detail":"; ".join((e.get("catalysts") or [])[:2]),"direction":e.get("direction","neutral")})

    def key(x):return x.get("date") or "9999-99-99"
    return sorted(items,key=key,reverse=True)[:15]
