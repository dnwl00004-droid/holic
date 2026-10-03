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
            for ticker in other:
                result.errors[ticker] = "rate_limited_429" if type(error).__name__ == "YFRateLimitError" else type(error).__name__
    return result
