
from __future__ import annotations
import os, json, hashlib
from pathlib import Path

SYSTEM = """You are a financial-filing extraction component.
Use only the supplied filing text. Do not recommend buying or selling.
Extract factual catalysts and changes. Distinguish management guidance from historical results.
Return concise valid JSON only with:
summary, direction (positive|negative|mixed|neutral), impact (high|medium|low),
guidance_changes[], catalysts[], risks[], dates[], numeric_claims[].
If evidence is insufficient, use neutral and empty arrays. Do not invent values."""

def analyze_filing_text(text:str, ticker:str, filing_type:str, filing_date:str,
                        model:str|None=None, cache_dir="data/cache/ai"):
    """
    Optional OpenAI call. Reads OPENAI_API_KEY from the environment only.
    The API key is never written to source files or output JSON.
    """
    key=os.getenv("OPENAI_API_KEY")
    if not key:return {"enabled":False,"reason":"OPENAI_API_KEY not set"}
    from openai import OpenAI
    model=model or os.getenv("OPENAI_MODEL","gpt-5-mini")
    clean=text[:45000]
    digest=hashlib.sha256((ticker+filing_type+filing_date+clean).encode()).hexdigest()[:24]
    p=Path(cache_dir)/f"{digest}.json"
    if p.exists():
        try:return json.loads(p.read_text(encoding="utf-8"))
        except Exception:pass
    prompt=f"""Ticker: {ticker}
Filing type: {filing_type}
Filing date: {filing_date}

FILING TEXT:
{clean}
"""
    client=OpenAI(api_key=key)
    response=client.responses.create(model=model,instructions=SYSTEM,input=prompt)
    raw=response.output_text.strip()
    try:
        if raw.startswith("```"):
            raw=raw.split("\n",1)[1].rsplit("```",1)[0].strip()
        data=json.loads(raw)
    except Exception:
        data={"summary":raw,"direction":"neutral","impact":"low","guidance_changes":[],"catalysts":[],"risks":[],"dates":[],"numeric_claims":[]}
    data.update({"enabled":True,"model":model,"ticker":ticker,"filing_type":filing_type,"filing_date":filing_date})
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    return data
