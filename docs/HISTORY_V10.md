# History Explorer v10

## Goal
The dashboard must show the full available historical series, not only the latest value or a 60/120-observation preview.

## Storage design
Historical data is split into separate static JSON files under `web/history/` instead of bloating `latest.json`.

- `history/fred/<series>.json` — full available macro series from public FRED CSV endpoints.
- `history/commodities/<symbol>.json` — max available daily futures history via yfinance.
- `history/market/<symbol>.json` — max available SPY/VIX/USD/rates/credit/crypto proxy history.
- `history/eia/<series>.json` — full weekly petroleum inventory history parsed from EIA historical tables.
- `history/calendar_archive.json` — historical release schedule archive.
- `history/index.json` — manifest used by the frontend.

The frontend fetches only the selected file. This keeps the initial dashboard fast even when MAX histories contain thousands of observations.

## History Explorer
The UI supports:

- Dataset selector
- Series selector
- Overlay selector
- 3M / 1Y / 5Y / 10Y / MAX ranges
- Historical line chart
- Start / end / min / max / range change / observation count
- Observation table
- Historical macro release archive
- Click-through from Macro and Commodity cards directly into the selected historical series

Overlay series are normalized to 100 at the first aligned observation, avoiding misleading dual-axis comparisons between incompatible units.

## Extra historical macro series
v10 adds several history-only series beyond the compact regime engine:

- Real GDP QoQ SAAR
- JOLTS job openings
- Initial jobless claims
- Average hourly earnings YoY
- PPI Final Demand YoY
- Michigan consumer sentiment
- Chicago Fed NFCI
- SOFR
- EFFR

## Important methodology note: revised history vs real-time vintage
The default FRED public-history files are the latest revised history as currently published. They do **not** necessarily equal the values investors saw on the original release date.

For true point-in-time macro backtests, add an ALFRED/FRED API-key workflow and store initial-release/vintage observations separately. Do not silently mix vintage data with revised history.

## Calendar archive limits
The current backfill focuses on official BLS schedules and parseable FOMC history, plus the current BEA schedule. Future daily runs preserve new calendar items. Consensus forecasts are not fabricated; they require a separate licensed/public forecast source.

## Build
```bash
python scripts/build_history_v10.py --snapshot web/latest.json --history-root web/history
```
