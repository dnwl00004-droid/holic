# v5 reference patterns

Clean-room UI/analytics patterns only.

- Sellside Research Engine: valuation + factors + risk + sentiment + macro in one analyst workbench.
- Market Intelligence Platform: market regime/breadth first, then sectors/stocks; divergence, drawdown, sentiment.
- FocusAlpha dashboards: guidance changes, filing events and 13F profile separated from raw market data.
- FinanceToolkit: transparent metric definitions and factor taxonomy; provenance matters more than a single "magic score".
- neurobloomai/market-tools: quality gate first, trend confirmation second.
- stock-market-analyzer: historical accuracy tracking and catalyst timeline.
- RyanJHamby/stock-screener: smart caching and market-regime filtering before stock signals.

v5 applies those patterns as:
1. fundamental quality panel,
2. insider/13F/short-activity panels,
3. macro tape,
4. optional AI filing extraction,
5. distinct Strength / Setup / Entry / Quality axes,
6. explicit source caveats.
