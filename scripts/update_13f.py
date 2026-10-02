
from pathlib import Path
import argparse, json
from src.providers.universe import load_sp500
from src.providers.institutional13f import download_dataset, load_information_table, aggregate_by_issuer, match_universe, DEFAULT_URL

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",default=DEFAULT_URL)
    ap.add_argument("--output",default="data/output/institutional13f.json")
    ap.add_argument("--min-score",type=float,default=92)
    a=ap.parse_args()
    z=download_dataset(a.url)
    df=load_information_table(z)
    agg=aggregate_by_issuer(df)
    matches=match_universe(agg,load_sp500(),a.min_score)
    out={"source":"SEC Form 13F flattened dataset","url":a.url,
         "mapping_method":"conservative normalized issuer-name match; confidence exposed",
         "matched_count":len(matches),"tickers":matches}
    p=Path(a.output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Wrote {p}: {len(matches)} matched tickers")
if __name__=="__main__":main()
