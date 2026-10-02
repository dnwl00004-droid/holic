
from __future__ import annotations
import pandas as pd
import requests
from io import StringIO
from pathlib import Path

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

def load_sp500() -> pd.DataFrame:
    """Prototype universe source. Returns ticker/company/sector/industry."""
    cache=Path("data/cache/universe.csv")
    try:
        r=requests.get(WIKI_SP500,headers={"User-Agent":"Mozilla/5.0 RS-Radar research"},timeout=30);r.raise_for_status()
        table=pd.read_html(StringIO(r.text))[0]
        if len(table)<400: raise ValueError("incomplete constituent list")
        cache.parent.mkdir(parents=True,exist_ok=True);table.to_csv(cache,index=False)
    except Exception:
        if not cache.exists(): raise
        table=pd.read_csv(cache)
    out = table[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]].copy()
    out.columns = ["ticker", "company", "sector", "industry"]
    # Yahoo uses BRK-B / BF-B rather than dots.
    out["provider_ticker"] = out["ticker"].str.replace(".", "-", regex=False)
    return out
