
from __future__ import annotations
import math, re
from typing import Iterable
from datetime import date

REVENUE_TAGS=["RevenueFromContractWithCustomerExcludingAssessedTax","SalesRevenueNet","Revenues"]
GROSS_TAGS=["GrossProfit"]
OPINC_TAGS=["OperatingIncomeLoss"]
NETINC_TAGS=["NetIncomeLoss"]
CFO_TAGS=["NetCashProvidedByUsedInOperatingActivities"]
CAPEX_TAGS=["PaymentsToAcquirePropertyPlantAndEquipment","PaymentsForPropertyPlantAndEquipment"]
ASSET_TAGS=["Assets"]
LIAB_TAGS=["Liabilities"]
EQUITY_TAGS=["StockholdersEquity","StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
CASH_TAGS=["CashAndCashEquivalentsAtCarryingValue","CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]
DEBT_TAGS=["LongTermDebtAndFinanceLeaseObligationsCurrent","LongTermDebtCurrent","LongTermDebtNoncurrent","LongTermDebt"]
SHARES_TAGS=["CommonStocksIncludingAdditionalPaidInCapitalMember","EntityCommonStockSharesOutstanding"]
INTEREST_TAGS=["InterestExpenseNonOperating","InterestExpense"]

def _usgaap(facts): return facts.get("facts",{}).get("us-gaap",{})

def _rows(facts,tags,units):
    ug=_usgaap(facts)
    for tag in tags:
        node=ug.get(tag,{}).get("units",{})
        for unit in units:
            vals=node.get(unit,[])
            if vals:
                return tag, vals
    return None, []

def _latest_annual_duration(facts,tags,units=("USD",),end=None):
    tag,vals=_rows(facts,tags,units);rows=[]
    for x in vals:
        frame=x.get("frame") or ""
        annual=bool(re.fullmatch(r"CY\d{4}",frame))
        if x.get("start") and x.get("end"):
            try:annual=300<=(date.fromisoformat(x["end"])-date.fromisoformat(x["start"])).days<=400
            except ValueError:continue
        if not annual or x.get("val") is None or end and x.get("end")!=end:continue
        rows.append({"frame":frame,"end":x.get("end"),"filed":x.get("filed"),"value":float(x["val"]),"tag":tag})
    return max(rows,key=lambda x:(x.get("end") or x["frame"],x.get("filed") or "")) if rows else None

def _latest_instant(facts,tags,units=("USD",),end=None):
    tag, vals=_rows(facts,tags,units)
    rows=[]
    for x in vals:
        if x.get("val") is None or not x.get("end"):continue
        # favor 10-K/10-Q reported values
        if x.get("form") not in {"10-Q","10-K"}:continue
        if end and x.get("end")!=end:continue
        rows.append((x.get("end"),x.get("filed") or "",float(x["val"])))
    if not rows:return None
    rows.sort()
    return {"end":rows[-1][0],"value":rows[-1][2],"tag":tag}

def _v(x): return None if not x else x["value"]
def _ratio(a,b,mult=1):
    if a is None or b in (None,0):return None
    return a/b*mult

def _round(x,n=2):
    return None if x is None or not math.isfinite(float(x)) else round(float(x),n)

def quality_snapshot(facts: dict, market_cap: float|None=None, price: float|None=None) -> dict:
    annual=_latest_annual_duration(facts,REVENUE_TAGS)
    annual_end=annual.get("end") if annual else None
    rev=_v(annual)
    gross=_v(_latest_annual_duration(facts,GROSS_TAGS,end=annual_end))
    op=_v(_latest_annual_duration(facts,OPINC_TAGS,end=annual_end))
    net=_v(_latest_annual_duration(facts,NETINC_TAGS,end=annual_end))
    cfo=_v(_latest_annual_duration(facts,CFO_TAGS,end=annual_end))
    capex=_v(_latest_annual_duration(facts,CAPEX_TAGS,end=annual_end))
    assets=_v(_latest_instant(facts,ASSET_TAGS,end=annual_end))
    liab=_v(_latest_instant(facts,LIAB_TAGS))
    equity=_v(_latest_instant(facts,EQUITY_TAGS,end=annual_end))
    cash=_v(_latest_instant(facts,CASH_TAGS))
    current=_v(_latest_instant(facts,[DEBT_TAGS[0],DEBT_TAGS[1]]))
    noncurrent=_v(_latest_instant(facts,[DEBT_TAGS[2]]))
    umbrella=_v(_latest_instant(facts,[DEBT_TAGS[3]]))
    debt=current+noncurrent if current is not None and noncurrent is not None else umbrella
    interest=_v(_latest_annual_duration(facts,INTEREST_TAGS,end=annual_end))
    fcf=None if cfo is None or capex is None else cfo-capex
    net_debt=None if debt is None or cash is None else debt-cash

    margins={
        "gross_margin_pct":_round(_ratio(gross,rev,100)),
        "operating_margin_pct":_round(_ratio(op,rev,100)),
        "net_margin_pct":_round(_ratio(net,rev,100)),
        "fcf_margin_pct":_round(_ratio(fcf,rev,100)),
    }
    quality={
        "roa_pct":_round(_ratio(net,assets,100)),
        "roe_pct":_round(_ratio(net,equity,100)),
        "debt_to_equity":_round(_ratio(debt,equity)),
        "liabilities_to_assets":_round(_ratio(liab,assets)),
        "interest_coverage":_round(_ratio(op,interest)) if interest not in (None,0) else None,
        "fcf":_round(fcf,0),
        "net_debt":_round(net_debt,0),
    }
    valuation={
        "market_cap":_round(market_cap,0),
        "price_to_earnings":_round(_ratio(market_cap,net)) if net is not None and net>0 else None,
        "ev_to_sales":_round(_ratio(market_cap+net_debt,rev)) if market_cap is not None and net_debt is not None else None,
        "price_to_sales":_round(_ratio(market_cap,rev)),
        "price_to_fcf":_round(_ratio(market_cap,fcf)) if fcf and fcf>0 else None,
        "fcf_yield_pct":_round(_ratio(fcf,market_cap,100)) if market_cap else None,
    }
    # transparent 0-100 quality score based only on available metrics
    pieces=[]
    gm=margins["gross_margin_pct"]; om=margins["operating_margin_pct"]; fm=margins["fcf_margin_pct"]
    roe=quality["roe_pct"]; de=quality["debt_to_equity"]; ic=quality["interest_coverage"]
    if gm is not None:pieces.append(max(0,min(100,gm*1.5)))
    if om is not None:pieces.append(max(0,min(100,50+om*2)))
    if fm is not None:pieces.append(max(0,min(100,50+fm*2)))
    if roe is not None:pieces.append(max(0,min(100,50+roe*1.5)))
    if de is not None:pieces.append(max(0,min(100,100-de*35)))
    if ic is not None:pieces.append(max(0,min(100,ic*10)))
    qscore=round(sum(pieces)/len(pieces)) if pieces else None
    base={
        "revenue":_round(rev,0),
        "operating_income":_round(op,0),
        "net_income":_round(net,0),
        "cfo":_round(cfo,0),
        "capex":_round(capex,0),
        "fcf":_round(fcf,0),
        "cash":_round(cash,0),
        "debt":_round(debt,0),
        "net_debt":_round(net_debt,0),
        "assets":_round(assets,0),
        "equity":_round(equity,0),
    }
    return {"base":base,"margins":margins,"quality":quality,"valuation":valuation,
            "quality_score":qscore,"annual_end":annual_end,"method":"matched fiscal-year annual flows; fiscal-year-end assets/equity; latest cash/debt for EV", "source":"SEC EDGAR CompanyFacts annual/instant facts"}
