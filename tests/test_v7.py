
from src.analytics.ranking_v7 import revision_score, expectation_gap, catalyst_score
from src.analytics.portfolio_risk_v7 import hypothetical_stress

def test_revision_score():
    e={"revision_pulse":{"change_30d_pct":5,"change_90d_pct":8,"net_30d":3},
       "surprise_summary":{"avg_last4_pct":4,"positive_last4":3}}
    x=revision_score(e)
    assert 0 <= x["score"] <= 100
    assert x["direction"]=="RISING"

def test_gap():
    x=expectation_gap({"available":True,"implied_revenue_growth_pct":12},{"revenue_growth_yoy":20})
    assert x["context_gap_pct"]==8

def test_stress():
    h=[{"value":60,"sector":"Technology"},{"value":40,"sector":"Energy"}]
    x=hypothetical_stress(h)
    assert "MARKET_-10" in x
