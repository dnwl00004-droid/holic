from src.providers.history_v10 import transform_history

def test_yoy_history():
    rows=[{"date":"2024-01-01","value":100},{"date":"2025-01-01","value":110}]
    x=transform_history(rows,"yoy")
    assert round(x[-1]["value"],1)==10.0

def test_level_history():
    rows=[{"date":"2025-01-01","value":4.25}]
    x=transform_history(rows,"level")
    assert x[0]["value"]==4.25
