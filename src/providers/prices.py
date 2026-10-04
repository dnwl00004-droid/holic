"""Instrument-aware adapters; never label ETF proxies as futures prices."""
from .nasdaq import download_daily as nasdaq_daily
from .yahoo import download_daily as yahoo_daily


class PriceFrames(dict):
    def __init__(self):
        super().__init__()
        self.errors = {}


def download_daily(tickers, period="3y"):
    equity = [t for t in tickers if not any(c in t for c in "=^") and t not in ("DX-Y.NYB", "BTC-USD")]
    other = [t for t in tickers if t not in equity]
    result = PriceFrames()
    if equity:
        quotes=nasdaq_daily(equity, period)
        result.update(quotes)
        result.errors.update(getattr(quotes,"errors",{}))
    if other:
        try:
            result.update(yahoo_daily(other, period))
        except Exception as error:
            # Keep a safe, actionable module identifier in Data Health. The
            # exception message may include provider URLs or account data.
            missing = getattr(error, "name", None) if isinstance(error, ModuleNotFoundError) else None
            code = "rate_limited_429" if type(error).__name__ == "YFRateLimitError" else type(error).__name__
            if missing and missing.replace("_", "").replace(".", "").isalnum():
                code += ":" + missing[:80]
            for ticker in other:
                result.errors[ticker] = code
    return result
