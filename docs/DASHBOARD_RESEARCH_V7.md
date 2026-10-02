# v7 research notes

## Portfolio-risk dashboards
Repeated successful patterns:
- correlation heatmap,
- risk contribution rather than capital weights only,
- VaR/drawdown/stress pages,
- explicit historical and hypothetical scenarios,
- deterministic cached data and reproducible calculations.

v7 copies the interaction pattern, not source code. The static browser Portfolio Lab
uses the 120-session chart data already present in the snapshot for correlations and
risk contribution. Historical crisis returns are precomputed by the v7 enrichment job.

## Catalyst architecture
The public Catalyst project separates macro/flow/supply/derivatives/trend layers and
keeps LLM prose grounded in computed layers. v7 applies the same architectural lesson:
our Catalyst Score is decomposed into Revision / Surprise / Insider / Technical / Quality.

## Backtest integrity
Signal scorecards recompute price/volume signals from historical bars. Current financial
quality is NOT injected into old signal dates. Remaining limitations are explicit:
- today's constituent universe (survivorship bias),
- no fees/slippage/taxes,
- end-of-day bars,
- corporate action/provider quality inherited from source data.

## Ranking
Revision ranking combines:
- 30-day estimate change,
- 90-day estimate change,
- net up/down revisions,
- earnings surprise history.

Reverse-DCF "expectation gap" compares current reported revenue YoY with the model's
constant five-year implied revenue growth. These horizons are not equivalent, so the
dashboard labels it as context rather than a valuation conclusion.
