# RS Radar v11 UI architecture

## Product goal
v11 deliberately keeps many tabs instead of aggressively hiding features. The project is still in discovery mode, so it is easier to remove a weak tab later than to lose a useful data domain now.

## Navigation
### Overview
- Today
- Stocks
- Market Health

### Macro
- Macro Overview
- Rates & Curve
- Inflation
- Growth & Labor
- Liquidity
- Credit
- FX & Dollar
- Housing
- Calendar
- History

### Commodities
- Overview
- Energy
- Metals
- Agriculture

### Discover
- Screener
- Groups
- RS Map
- Setups
- Ranks

### Research
- Research
- Intelligence
- Compare

### Validate
- Replay
- Portfolio & Alerts
- Data Health

## Key UX decisions
- Persistent left navigation on desktop, horizontal scrolling navigation on mobile.
- Global command/search field for stocks and historical macro series.
- Today is the default landing page.
- Dedicated macro and commodity tabs read from the same historical database, so data is not duplicated.
- Metric cards link directly into History Explorer.
- Data Health exposes provider provenance and historical coverage.
- Compact density toggle is available in the header.

## Historical data additions queued in v11
Verified FRED series added to the build registry include:
- DGS3MO, DGS5, DFII5, T5YIE
- AAA10Y, BAA10Y, STLFSI4
- U6RATE, CIVPART, PERMIT, MORTGAGE30US
- DEXKOUS
- DCOILWTICO, DCOILBRENTEU, DHHNGSP

The daily GitHub workflow already runs `build_history_v10.py`, so these series are automatically backfilled into `web/history/` during the next connected build.

## Data philosophy
Current cards, full history, event calendars, and derived scores remain separate layers. Raw/source data should never be overwritten by model summaries or heuristic scores. Revised FRED history is labeled as such; point-in-time vintage data remains a separate future layer.
