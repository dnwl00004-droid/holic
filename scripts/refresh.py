"""Validated refresh entrypoint. No paid APIs and no demo fallback."""
from __future__ import annotations
import argparse, copy, json, os, shutil, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.reliability import atomic_json, blank_snapshot, is_demo, now, read_json, validate_snapshot, valid_history
from src.providers.live_history import build_official_history, REGISTRY
from src.providers.macro_official_v8 import nyfed_reference_rates
from src.analytics.macro_v8 import macro_scores, sector_macro_fit
from src.refresh_support import run_provider_job, history_provider_health, snapshot_stamp

def refresh(web="web", macro_only=False, extended=False, selected=None):
    web = Path(web).resolve(); web.mkdir(parents=True, exist_ok=True)
    previous = read_json(web / "latest.json", {})
    if is_demo(previous): previous = {}
    snap = copy.deepcopy(previous) if previous else blank_snapshot()
    health = []; attempted = now()
    # All stages run in isolation. Failed jobs cannot corrupt the published snapshot.
    with tempfile.TemporaryDirectory(prefix="rs-refresh-", dir=ROOT) as td:
        staging = Path(td); history = staging / "history"
        if (web / "history").exists(): shutil.copytree(web / "history", history)
        candidate = staging / "latest.json"; atomic_json(candidate, snap)
        signal_log = staging / "signal_log.json"
        prior_signals = ROOT / "data/output/signal_log.json"
        if prior_signals.exists(): shutil.copy2(prior_signals, signal_log)
        def stage(label, command, timeout=240):
            before = read_json(candidate, {})
            stage_attempt = now(); stage_started = time.monotonic()
            try:
                duration = run_provider_job(label, command, cwd=ROOT, timeout=timeout)
                after = read_json(candidate); validate_snapshot(after)
                if label == "Yahoo Finance / equity universe":
                    for key in ("macro_v8","macro_v9","data_health","history_v10","signal_backtests","revision_rankings","stress_library"):
                        if key not in after and key in before: after[key] = before[key]
                    after["sources"] = {**before.get("sources",{}),**after.get("sources",{})}
                    atomic_json(candidate,after)
                health.append({"source": label, "status": "ok", "last_attempt": stage_attempt, "last_success": now(), "duration_seconds": duration, "error": None})
                return True
            except Exception as e:
                atomic_json(candidate, before)
                prior_health=next((p for p in previous.get("data_health",{}).get("providers",[]) if p.get("source")==label),{})
                error = type(e).__name__ + ":" + str(e)[:80]
                print(f"[refresh] {label}: retained verified cache ({error})", flush=True)
                health.append({"source": label, "status": "stale" if before.get("tickers") else "unavailable", "last_attempt": stage_attempt, "last_success": prior_health.get("last_success"), "duration_seconds": round(time.monotonic()-stage_started, 2), "error": error})
                return False
        stocks_ok = False
        if not macro_only:
            args = ["-m", "src.build_snapshot", "--output", str(candidate), "--signal-log", str(signal_log)]
            if os.environ.get("SEC_USER_AGENT"): args.append("--with-sec")
            stocks_ok = stage("Yahoo Finance / equity universe", args, 600)
            if stocks_ok and extended:
                if os.environ.get("SEC_USER_AGENT"):
                    stage("SEC / FINRA", ["-m", "scripts.enrich_v5", "--snapshot", str(candidate), "--with-finra", "--top", "80"], 1200)
                stage("Yahoo estimates / replay", ["-m", "scripts.enrich_v6", "--snapshot", str(candidate), "--with-replay", "--top", "80"], 600)
                stage("Signal backtests", ["-m", "scripts.enrich_v7", "--snapshot", str(candidate), "--with-signal-backtest", "--with-stress-library", "--backtest-top", "50"], 600)
        else:
            prior=next((p for p in previous.get("data_health",{}).get("providers",[]) if p.get("source") in ("Yahoo Finance / equity universe","Yahoo Finance / equities")),{})
            health.append({"source":"Yahoo Finance / equity universe","status":"stale" if snap.get("tickers") else "unavailable","last_success":None,"last_attempt":None,"error":"not yet collected",**prior,"refresh_note":"Skipped in macro-only run"})
        snap = read_json(candidate)
        fred_started = time.monotonic()
        print("[refresh] FRED official histories: started", flush=True)
        items = build_official_history(history, selected=selected)
        if selected:
            touched = {x["id"] for x in items}
            items += [x for x in read_json(history / "index.json", {}).get("items", []) if x["id"] not in touched and "demo" not in str(x.get("source", "")).lower() and x.get("id") in REGISTRY]
        health.append({**history_provider_health("FRED official histories", items), "duration_seconds": round(time.monotonic()-fred_started, 2)})
        fred = {}
        for item in items:
            h = read_json(staging / item["path"], {}) if item.get("path") else {}
            rows = h.get("history", []); last = rows[-1] if rows else {}
            raw = [{"date": x["date"], "value": x.get("raw", x["value"])} for x in rows]
            change = None
            if raw:
                import pandas as pd
                from src.providers.macro_official_v8 import _change
                change = _change(raw)
            fred[item["id"]] = {**REGISTRY.get(item["id"], {}), "value": last.get("value"), "date": last.get("date"), "source": "FRED", "source_url": "https://fred.stlouisfed.org/series/" + item["id"],
                                "history": rows[-60:], "change_3m_raw": change, "status": item.get("status"), "error": item.get("error"), "last_update": item.get("last_success"), "method": item.get("method"), "vintage": "revised"}
        try:
            ny = nyfed_reference_rates()
        except Exception:
            ny = {"SOFR": {"value": None}, "EFFR": {"value": None}}
        for k, val in ny.items():
            old = previous.get("macro_v8", {}).get("nyfed", {}).get(k, {})
            if val.get("value") is None and old.get("value") is not None: ny[k] = {**old, "status": "stale", "error": val.get("error")}
            elif val.get("value") is not None:
                ny[k].update(status="ok",last_attempt=now(),last_success=now())
        for k in ("SOFR","EFFR"):
            val=ny.get(k,{})
            if val.get("value") is None and fred.get(k,{}).get("value") is not None:
                ny[k]={**fred[k],"source":"FRED reference-rate series","upstream_error":val.get("error")}
        sofr,effr=ny.get("SOFR",{}),ny.get("EFFR",{})
        if sofr.get("date") and sofr.get("date")==effr.get("date") and sofr.get("value") is not None and effr.get("value") is not None:
            ny["SOFR_EFFR_SPREAD_BP"]={"value":round((sofr["value"]-effr["value"])*100,4),"date":sofr["date"],"unit":"bp","source":"same-date SOFR minus EFFR","method":"(SOFR - EFFR) × 100"}
        else: ny.pop("SOFR_EFFR_SPREAD_BP",None)
        regime = macro_scores(fred, ny)
        snap["macro_v8"] = {**snap.get("macro_v8", {}), "fred": fred, "nyfed": ny, "regime": regime, "gdpnow": {"value": None, "source": "Atlanta Fed", "status": "unavailable", "error": "commentary parser requires verification"}}
        for rec in snap.get("tickers", []): rec.setdefault("v8", {})["macro_fit"] = sector_macro_fit(rec.get("sector"), regime)
        if extended:
            from src.providers.assets_live import collect_assets
            asset_output = staging / "asset-result.json"
            asset_started = time.monotonic(); asset_error = None
            try:
                run_provider_job("Yahoo Finance / market and futures", ["-m", "src.providers.assets_live", "--history-root", str(history), "--output", str(asset_output)], cwd=ROOT, timeout=300)
                result = read_json(asset_output)
                asset_items, commodities, market_assets = result["items"], result["commodities"], result["market"]
            except Exception as e:
                error_code = type(e).__name__ + ":" + str(e)[:80]
                asset_error = error_code
                print(f"[refresh] Market and futures: retained verified cache ({error_code})", flush=True)
                def unavailable(*args, **kwargs):
                    raise RuntimeError(error_code)
                asset_items, commodities, market_assets = collect_assets(history, fetch=unavailable)
            items.extend(asset_items)
            asset_health = history_provider_health("Yahoo Finance / market and futures", asset_items)
            asset_health["duration_seconds"] = round(time.monotonic()-asset_started, 2)
            if asset_error: asset_health["error"] = asset_error
            health.append(asset_health)
            snap.setdefault("macro_v9",{})["commodities"] = commodities
            snap["macro_v8"]["market"] = market_assets
        else:
            items.extend(x for x in read_json(history/"index.json",{}).get("items",[]) if x.get("kind") in ("commodity","market","derived") and not is_demo(x))
        # Use the verified schedule parser in every refresh mode.
        try:
            from src.providers.calendar_live import official_calendar
            snap.setdefault("macro_v9", {})["calendar"] = official_calendar()
        except Exception as e:
            snap.setdefault("macro_v9", {})["calendar"] = {**previous.get("macro_v9", {}).get("calendar", {"events": []}), "error": type(e).__name__, "status": "stale" if previous else "unavailable"}
        cal = snap.get("macro_v9", {}).get("calendar", {})
        failed_sources={p["source"] for p in cal.get("providers",[]) if p.get("status")=="unavailable"}
        if failed_sources:
            prior_events=previous.get("macro_v9",{}).get("calendar",{}).get("events",[])
            cal.setdefault("events",[]).extend({**e,"status":"stale"} for e in prior_events if e.get("source") in failed_sources)
        from src.providers.eia_live import build_eia
        eia_started = time.monotonic()
        print("[refresh] EIA official histories: started", flush=True)
        eia_items=build_eia(history)
        health.append({**history_provider_health("U.S. EIA inventories", eia_items), "duration_seconds": round(time.monotonic()-eia_started, 2)})
        items.extend(eia_items)
        inventories={}
        for item in eia_items:
            d=read_json(staging/item["path"],{}) if item.get("path") else {}
            h=d.get("history",[])
            inventories[item["id"]]={**item,"value":h[-1]["value"] if h else None,"date":h[-1]["date"] if h else None,"weekly_change":h[-1]["value"]-h[-2]["value"] if len(h)>1 else None,"history":h[-80:]}
        snap.setdefault("macro_v9",{})["eia_inventories"]=inventories
        events = cal.pop("archive_events", []) + cal.get("events", [])
        old_archive = read_json(history / "calendar_archive.json", {})
        if is_demo(old_archive) or previous.get("meta",{}).get("calendar_parser")!="official_v13": old_archive = {}
        combined = {(e.get("date"), e.get("title"), e.get("source")): e for e in old_archive.get("events", []) + events if e.get("date")}
        atomic_json(history / "calendar_archive.json", {"events": sorted(combined.values(), key=lambda e: e["date"]), "source": "Official provider schedules", "start_year": min([int(e["date"][:4]) for e in combined.values()] or [datetime.now().year]), "end_year": datetime.now().year, "updated_at": now()})
        from src.providers.commodities_v9 import COMMODITIES
        contracts=snap.setdefault("macro_v9",{}).setdefault("commodities",{}).setdefault("contracts",{})
        ids={x["id"] for x in items}
        for sid,meta in COMMODITIES.items():
            if sid not in ids:
                prior_item=next((x for x in read_json(history/"index.json",{}).get("items",[]) if x["id"]==sid and x.get("path")),None)
                if prior_item:
                    prior_item.update(status="stale",error="commodity source not refreshed")
                    items.append(prior_item)
                else:
                    items.append({"id":sid,"kind":"commodity",**meta,"count":0,"path":None,"source":"Yahoo Finance / yfinance","status":"unavailable","error":"price feed unavailable or not collected","last_attempt":None,"last_success":None})
            contracts.setdefault(sid,{**meta,"value":None,"date":None,"source":"Yahoo Finance / yfinance","status":"unavailable","error":"price feed unavailable or not collected"})
        counts = {kind: sum(x.get("kind") == kind and x.get("count", 0) > 0 for x in items) for kind in ("fred", "commodity", "market", "eia", "derived")}
        counts["commodities"] = counts.pop("commodity"); counts["calendar_events"] = len(combined)
        index = {"schema_version": "13.0", "items": items, "counts": counts, "updated_at": now(), "calendar_path": "history/calendar_archive.json"}
        atomic_json(history / "index.json", index); atomic_json(history / "manifest.json", index)
        snap["history_v10"] = {"index_path": "history/index.json", "calendar_path": "history/calendar_archive.json", "counts": counts}
        snap["sources"]["official_history"] = "FRED official/revised series, per-series source links"
        snap["sources"]["reference_rates"] = "Federal Reserve Bank of New York"
        snap["data_health"] = {"providers": health, "series": items, "updated_at": now()}
        snap["meta"].update(calendar_parser="official_v13",schema_version="14.0", demo=False, last_refresh_attempt=attempted, last_refresh_completed=now(), universe_count=len(snap.get("tickers", [])), status="partial" if any(x.get("status") != "ok" for x in items+health+cal.get("providers",[])) or not stocks_ok else "ok")
        validate_snapshot(snap)
        # Verify every manifest-linked history before promoting any data.
        for item in items:
            if item.get("path") and not valid_history(read_json(staging / item["path"], {}).get("history")): raise ValueError("manifest points to invalid history")
        if previous:
            stamp = snapshot_stamp(previous)
            atomic_json(web / "snapshots" / (stamp + ".json"), previous)
        for src in history.rglob("*.json"):
            atomic_json(web / "history" / src.relative_to(history), read_json(src))
        if stocks_ok and signal_log.exists(): atomic_json(prior_signals, read_json(signal_log))
        atomic_json(web / "latest.json", snap)
        print(json.dumps({"stocks": len(snap["tickers"]), "history": counts, "status": snap["meta"]["status"], "failed_series": [x["id"] for x in items if x.get("status") == "unavailable"]}))
    return snap

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--web", default="web"); ap.add_argument("--macro-only", action="store_true"); ap.add_argument("--extended", action="store_true"); ap.add_argument("--series", nargs="+")
    a = ap.parse_args(); refresh(a.web, a.macro_only, a.extended, a.series)
