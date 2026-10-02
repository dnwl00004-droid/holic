# Dashboard research notes — v4

This project uses clean-room implementations. We did not paste third-party source code.

## Strong references inspected

### OpenBB
- Very large open-source financial-data ecosystem.
- Key pattern adopted: provider abstraction / "connect once, consume everywhere".
- License: AGPLv3 upstream, so this project does not copy OpenBB source.

### xang1234/stock-screener
- Multi-market scanner with 80+ filters, breadth, group rankings, theme discovery,
  validation, options command center and static GitHub Pages output.
- Key patterns adopted: multi-screener badges, group rankings, market breadth as a
  first-class page, one canonical calculation layer.
- License: Apache-2.0. We still implemented our own formulas rather than copying code.

### jwbradley/MarketBreadth
- Strong separation of market regime -> sector -> stock -> setup -> entry.
- Breadth includes A/D, up/down volume, highs/lows, Zweig-style breadth thrust.
- Key pattern adopted: separate setup quality from entry timing; expected-move is a later candidate.
- License: CC0 1.0.

### iArpanK/RS-Screener
- Useful discovery concept: relative-strength new high and RS new high before price.
- Key pattern adopted: independent `RS new high before price` signal using our RS line.

### BB-Terminal
- Bloomberg-like interface, OpenBB data layer, rules engine that turns metrics into signals.
- Key pattern adopted: signal badges / rules layer rather than raw metrics only.

### FocusAlpha dashboards
- MIT examples use baked static data and interactive self-contained dashboards.
- Useful patterns: event/guidance changes, ownership panels, single-file frozen snapshot,
  and explicit caveats around what a data point does and does not mean.

### FinanceToolkit
- Broad metric taxonomy: efficiency, liquidity, profitability, solvency, valuation;
  rolling/trailing calculations and custom ratios.
- v5 candidate: SEC-derived quality/solvency/valuation factor packs.

## v4 features derived from the research

- Market-health page
- A/D ratio and cumulative participation context
- Up/down volume ratio
- % above 20/40/50/200DMA
- 52-week highs/lows
- 4% daily movers
- 25% quarterly movers
- breadth-thrust proxy
- ATR-extension counts
- market-quality composite
- RS-new-high and RS-new-high-before-price
- volume-breakthrough signal
- RSI/OBV divergence proxies
- 9-bar exhaustion proxy
- Strength vs Setup vs Entry scores
- sector/group rankings
- multi-screen badges
- cached SEC quarterly EPS/revenue YoY enrichment
