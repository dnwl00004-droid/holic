# v6 dashboard research notes

## Patterns incorporated

### Sellside Research Engine
- Reverse DCF as a first-class "what is priced in?" tool.
- Earnings revisions, surprises and risk next to valuation.
- Static dashboard refreshed by scheduled data jobs.

### valuationengine
- Pure calculation engine separated from I/O and UI.
- Reverse DCF solver and sensitivity thinking.
- Assumptions made visible instead of hidden.

### KarneeshkarV/screener
- Persist a screen run and replay it later.
- Point-in-time historical backtesting as a distinct mode.

### stock-analysis
- Explicitly distinguishes honest price-only historical replay from composite
  backtests that would leak today's fundamentals into the past.
- v6 adopts that warning: replay recomputes price/volume only.

### paper-trail / mkt
- Watchlists, condition-based alerts and recorded/replayed signals.
- v6 uses browser-local watchlists and browser notifications only while open.

### stock-analyzer / Stock-Market-Intelligence
- Portfolio analysis, correlation/exposure workflows, alert center and AI research
  as separate dashboard pages rather than overloading a single stock card.

## v6 implementation decisions

1. Reverse DCF solves the constant 5-year revenue growth implied by current EV.
2. WACC/terminal-growth/FCF-margin assumptions are visible.
3. Yahoo EPS trend/revisions and earnings surprise are labeled provider data.
4. Historical replay is technical-only and keeps a survivorship-bias caveat.
5. Watchlists/portfolio are stored locally in the browser; no brokerage actions.
6. Catalyst timeline merges revisions, earnings, Form 4, technical changes and
   optional AI-extracted filing events.
