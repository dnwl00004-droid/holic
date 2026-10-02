
from __future__ import annotations
from pathlib import Path
import io, zipfile, re, unicodedata, requests
import pandas as pd
from rapidfuzz import fuzz

DEFAULT_URL="https://www.sec.gov/files/datastandardsinnovation/data/form-13f-data-sets/01jun2026-31aug2026_form13f.zip"
HEADERS={"User-Agent":"RS-Radar research contact@example.com"}

def normalize_name(s):
    s=unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().upper()
    s=re.sub(r"\b(INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LTD|LIMITED|PLC|HOLDINGS|HOLDING|GROUP|CLASS [A-Z])\b"," ",s)
    s=re.sub(r"[^A-Z0-9 ]+"," ",s);return re.sub(r"\s+"," ",s).strip()

def download_dataset(url=DEFAULT_URL, cache_file="data/cache/13f/latest.zip"):
    p=Path(cache_file);p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        r=requests.get(url,headers=HEADERS,timeout=120);r.raise_for_status();p.write_bytes(r.content)
    return p

def load_information_table(zip_path):
    z=zipfile.ZipFile(zip_path)
    names=z.namelist()
    # SEC flattened set normally contains INFOTABLE.tsv
    cand=next((n for n in names if "INFOTABLE" in n.upper()),None)
    if not cand:raise RuntimeError("INFOTABLE file not found in SEC 13F ZIP")
    with z.open(cand) as f:
        return pd.read_csv(f,sep="\t",dtype=str,low_memory=False)

def aggregate_by_issuer(df:pd.DataFrame)->pd.DataFrame:
    cols={c.upper():c for c in df.columns}
    issuer=next((cols[k] for k in cols if "NAMEOFISSUER" in k.replace("_","")),None)
    value=next((cols[k] for k in cols if k=="VALUE" or k.endswith("_VALUE")),None)
    shares=next((cols[k] for k in cols if "SSHPRNAMT" in k.replace("_","")),None)
    if not issuer:raise RuntimeError("Issuer column not found")
    x=df.copy();x["_norm"]=x[issuer].map(normalize_name)
    if value:x["_value"]=pd.to_numeric(x[value],errors="coerce").fillna(0)
    else:x["_value"]=0
    if shares:x["_shares"]=pd.to_numeric(x[shares],errors="coerce").fillna(0)
    else:x["_shares"]=0
    g=x.groupby("_norm",as_index=False).agg(manager_rows=("_norm","size"),value_thousands=("_value","sum"),shares=("_shares","sum"))
    return g

def match_universe(agg:pd.DataFrame, universe:pd.DataFrame, min_score=92)->dict[str,dict]:
    """
    Conservative issuer-name mapping. Returns only high-confidence matches and explicitly reports confidence.
    It does NOT pretend CUSIP is a ticker.
    """
    names=agg["_norm"].tolist(); rowmap={r["_norm"]:r for _,r in agg.iterrows()}
    out={}
    for _,u in universe.iterrows():
        target=normalize_name(u["company"])
        if not target:continue
        exact=rowmap.get(target)
        if exact is not None:
            out[u["ticker"]]={"match_confidence":100,"matched_issuer":target,
                              "manager_rows":int(exact["manager_rows"]),"reported_value_thousands":float(exact["value_thousands"]),
                              "reported_shares":float(exact["shares"])}
            continue
        # Fuzzy only if extremely high similarity
        best=None;bestscore=0
        for n in names:
            sc=fuzz.token_set_ratio(target,n)
            if sc>bestscore:bestscore=sc;best=n
        if best and bestscore>=min_score:
            r=rowmap[best]
            out[u["ticker"]]={"match_confidence":round(bestscore,1),"matched_issuer":best,
                              "manager_rows":int(r["manager_rows"]),"reported_value_thousands":float(r["value_thousands"]),
                              "reported_shares":float(r["shares"])}
    return out
