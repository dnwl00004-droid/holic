
from src.analytics.valuation_v6 import reverse_dcf_implied_growth
from src.analytics.portfolio_v6 import analyze_portfolio

def test_reverse_dcf():
    x=reverse_dcf_implied_growth(100_000,0,100_000,10,wacc=.10,terminal_growth=.025)
    assert x["available"]
    assert -30 <= x["implied_revenue_growth_pct"] <= 80

def test_portfolio():
    snap={"tickers":[{"ticker":"AAA","sector":"Tech","price":{"close":10},"scores":{"strength":80,"entry":75},"rs":{"score":90}}]}
    x=analyze_portfolio([{"ticker":"AAA","shares":10}],snap)
    assert x["total_value"]==100
    assert x["weighted_rs"]==90
