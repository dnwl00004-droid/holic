
from src.analytics.macro_v8 import macro_scores, sector_macro_fit
def test_macro_scores():
    fred={"UNRATE":{"value":4.0},"PAYEMS":{"value":450},"INDPRO":{"value":2},"RSAFS":{"value":4},"HOUST":{"value":3},
          "CPIAUCSL":{"value":2.5},"CPILFESL":{"value":2.7},"PCEPILFE":{"value":2.6},"T10YIE":{"value":2.3},
          "M2SL":{"value":4},"BAMLH0A0HYM2":{"value":3},"BAMLC0A0CM":{"value":.8},
          "DFF":{"value":4},"DFII10":{"value":2},"T10Y2Y":{"value":.5}}
    x=macro_scores(fred,{"SOFR_EFFR_SPREAD_BP":{"value":2}},{"value":3},{})
    assert x["regime"] in {"GOLDILOCKS","REFLATION","STAGFLATION","DISINFLATION_SLOWDOWN"}
    assert 0 <= x["macro_risk_score"] <= 100
    assert 0 <= sector_macro_fit("Technology",x)["score"] <= 100
