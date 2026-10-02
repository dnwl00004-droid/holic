
import argparse,json
from pathlib import Path
from src.ai.filing_analyst import analyze_filing_text

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--ticker",required=True)
    ap.add_argument("--type",default="8-K")
    ap.add_argument("--date",required=True)
    ap.add_argument("--output")
    a=ap.parse_args()
    text=Path(a.file).read_text(encoding="utf-8",errors="ignore")
    result=analyze_filing_text(text,a.ticker,a.type,a.date)
    raw=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:Path(a.output).write_text(raw,encoding="utf-8")
    print(raw)
if __name__=="__main__":main()
