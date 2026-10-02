# v5 data-source map

| Feature | Source | Refresh | Notes |
|---|---|---|---|
| Price / OHLCV | Yahoo Finance via yfinance | daily | prototype/non-commercial caveat |
| Financial statements / margins | SEC CompanyFacts | weekly cache / daily build | audited filed facts |
| Insider open-market P/S | SEC Form 4 | daily for top candidates | P/S only; awards/exercises excluded |
| Institutional holdings | SEC Form 13F flattened quarterly dataset | quarterly | issuer-name mapping confidence is exposed |
| Short sale volume | FINRA Reg SHO daily short sale volume | daily | NOT short interest |
| Macro proxies | Yahoo Finance | daily | SPY, VIX, 10Y proxy, DXY, WTI, gold, BTC |
| Options | Alpaca | optional | indicative feed can be free; credentials required |
| Filing AI extraction | OpenAI Responses API | optional/event-driven | API key only from environment; cached output |

## Important distinctions

- 13F is delayed quarterly and covers reportable long US-listed positions; it is not real-time institutional flow.
- FINRA daily short-sale volume is transaction volume, not outstanding short interest.
- Form 4 open-market purchase/sale codes are emphasized because grants and option exercises have different economic meaning.
- AI extraction is a text-extraction layer. It must not overwrite numeric source data.
