from __future__ import annotations
import argparse,json
from pathlib import Path
from src.providers.commodities_v9 import commodity_snapshot,eia_inventory_snapshot
from src.providers.calendar_v9 import macro_calendar_snapshot

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--snapshot",default="web/latest.json");a=ap.parse_args()
    p=Path(a.snapshot);snap=json.loads(p.read_text(encoding="utf-8"))
    try:commodities=commodity_snapshot()
    except Exception as e:commodities={"contracts":{},"derived":{},"breadth":{},"error":type(e).__name__}
    try:eia=eia_inventory_snapshot()
    except Exception as e:eia={"error":type(e).__name__}
    try:calendar=macro_calendar_snapshot()
    except Exception as e:calendar={"events":[],"error":type(e).__name__}
    snap["macro_v9"]={"commodities":commodities,"eia_inventories":eia,"calendar":calendar}
    snap["meta"]["schema_version"]="9.0"
    snap["sources"]["macro_v9"]={
      "commodities":"Yahoo Finance futures via yfinance",
      "energy_inventories":"U.S. EIA weekly petroleum history pages",
      "calendar":"Federal Reserve + BLS + BEA + EIA + U.S. Treasury + OPEC official schedules",
      "note":"Event dates remain source-dependent; OPEC dates can be changed by later press releases."
    }
    p.write_text(json.dumps(snap,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("v9 commodity + calendar enrichment complete")
if __name__=="__main__":main()
