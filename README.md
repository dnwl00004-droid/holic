# RS Radar v15

Repository: [dnwl00004-droid/holic](https://github.com/dnwl00004-droid/holic).
For current deployment setup and remaining data limitations, see
[WORK_HANDOFF.md](WORK_HANDOFF.md).

The first publish validates the saved genuine data without waiting for the
long refresh. Weekday refreshes then validate new responses and republish.
Enable **Settings → Pages → Source → GitHub Actions** once to activate Pages.

A clean-room, static-first U.S. equity relative-strength / setup screener.

## Architecture

1. `src/providers/` collects the universe, OHLCV and SEC fundamentals.
2. `src/analytics/` calculates RS, trend template, Weinstein-style stage proxy,
   VCP/setup heuristics, market breadth and composite score.
3. `src/build_snapshot.py` produces `web/latest.json`.
4. `web/` is a zero-backend HTML/CSS/JS dashboard deployable to GitHub Pages.
5. GitHub Actions can rebuild the snapshot after the U.S. close.

## Data provenance

- Stocks, benchmark, sector ETFs and commodity-linked ETFs: validated Nasdaq public daily quotes
- Futures and other Yahoo-only instruments: Yahoo Finance via `yfinance`, with explicit N/A when unavailable
- Fundamentals: SEC EDGAR CompanyFacts API
- Benchmark: SPY via the same price provider
- Universe: S&P 500 list from Wikipedia for prototype use
- Derived fields: calculated locally; see `sources` and `methodology` in JSON

Daily quote history uses provider-reported split adjustments and excludes cash
dividends. Rankings align every stock to the SPY observation date. Malformed
OHLCV, wrong symbols, incomplete pages and large unexplained price discontinuities
are excluded; validated caches remain available during provider outages.
Commodity-linked ETF prices are USD per fund share and remain separate from
spot prices and futures contracts. Analyst estimates require `--with-estimates`;
the default refresh does not request an unavailable estimate feed.

The market history collector also requests QQQ, IWM and the eleven U.S. sector
ETFs (XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY). The Sector
screen labels these as fund-share prices with source dates; missing quotes
remain unavailable. They are separate from the constituent group RS rankings.

The header has three saved design presets (Terminal, Editorial and High
contrast) and Korean/English UI selection. Preferences stay in this browser.
The translation covers navigation, common controls, status and major screens;
source names and financial identifiers retain their official spelling.

For a public/commercial product, review exchange/vendor licensing and replace the
prototype quote provider if redistribution rights are required.

## Quick demo

Run `python start_dashboard.py` or use `START_WINDOWS.cmd`.
Production refuses illustrative payloads and shows unavailable states on failure.
See `QUICK_START_KO.md` and `VERIFICATION_REPORT.md` for current connectivity and limits.

For a local web server:

```bash
python -m http.server 8000 -d web
```

then open http://localhost:8000

## Build live snapshot

```bash
pip install -r requirements.txt
python -m src.build_snapshot --output web/latest.json
```

Network access is required.

## Methodology notes

### RS Score
Weighted price momentum:
- 63d: 40%
- 126d: 20%
- 189d: 20%
- 252d: 20%

Raw scores are percentile-ranked across the current universe to 1..99.

### Short RS
21-trading-day change in `stock_adjusted_close / SPY_adjusted_close`, then
percentile-ranked across the universe.

### Trend template
Transparent proxy inspired by common growth-stock trend criteria. It is not an
official or licensed IBD/MarketSurge score.

### Stage
A transparent Weinstein-style proxy using price vs 200DMA, 50DMA vs 200DMA,
200DMA slope and long-range position.

### VCP
Heuristic detector using local pivot contractions and volume dry-up. It is a
research aid, not a guaranteed chart-pattern classifier.

## Important

Names such as IBD RS Rating and RRG/JdK RS-Ratio are proprietary/trademarked
concepts. This project uses its own `RS Score`, `RS Momentum`, and
`RS Dynamics` formulas and should not imply official affiliation.


## v2 additions

- **Strength vs Setup**: structural leadership and current actionability are scored separately.
- **5-axis profile**: RS / Trend / Setup / Growth / Volume.
- **Desktop 3-panel workbench**: leader list, price/why panel, profile/insight panel.
- **Compare**: four-stock side-by-side comparison.
- **Signal log + scorecard**: new setups are logged and evaluated after 20 trading days.
- **Today changes**: compares the new snapshot with the previous `latest.json`.

The UI is an original clean-room implementation inspired by common dashboard interaction patterns. It does not copy third-party source code or proprietary formulas.


## v3 additions

- **Peer-relative Factor Grades**: our own sector-relative grades for RS, Trend, Setup, Volume and (when data exists) Growth.
- **Screen Lab**: no-paid-API natural-language-like filter parser plus preset screen recipes.
- **Rating History**: rolling snapshot history for Strength, Setup and RS.
- **Warning Flags**: technical risk flags for weakening RS, below-50DMA, extension, Stage 4, high ATR and distance from 52-week high.
- **Period Performance**: 1W / 1M / 3M / 6M / 12M return strip.
- **Risk Metrics**: ATR%, annualized 20-day volatility, 52-week-high distance and 90-day max drawdown.

These features are clean-room implementations inspired by common patterns found in research platforms. Third-party proprietary ratings and formulas are not copied.


## v4 additions

- **Market Health**: advance/decline, up/down volume, 20/40/50/200DMA participation,
  52-week highs/lows, 4% daily movers, 25% quarterly movers, breadth-thrust proxy,
  ATR-extension breadth and an auditable market-quality score.
- **Strength / Setup / Entry**: three separate axes. A strong setup can now explicitly
  be marked as a poor current entry.
- **RS Leads Price**: flags relative-strength lines at a 52-week high before price.
- **Multi-Screener Badges**: Trend Leader, Growth Leader, VCP Ready, Volume Breakthrough,
  RS New High, RS-before-Price and Clean Trend.
- **Group Rankings**: sector-level RS, short RS, performance, participation, setup count
  and entry-ready count.
- **Technical context**: RSI(14), RSI/OBV divergence proxies and a transparent
  9-bar exhaustion proxy.
- **SEC enrichment**: optional/cached quarterly EPS and revenue YoY from CompanyFacts;
  GitHub Actions now runs it by default with an Actions cache.
- **Research notes**: `docs/DASHBOARD_RESEARCH_V4.md`.

All borrowed ideas are reimplemented independently. Proprietary ratings or branded formulas
are not claimed to be official implementations.
## v5 additions

- SEC-based **Fundamental Quality**: margins, ROA/ROE, debt/equity, interest coverage, FCF and a transparent quality score.
- SEC **Form 4 Insider Activity**: open-market P/S transactions only; grants/exercises are not mixed into the signal.
- SEC **13F institutional snapshot**: quarterly flattened dataset adapter with conservative issuer-name matching and visible confidence.
- FINRA **daily short-sale volume** adapter with a hard caveat that it is not short interest.
- **Macro Tape**: SPY / VIX / 10Y proxy / dollar / WTI / gold / bitcoin context.
- Optional **Alpaca option-chain** adapter; calculations only when the feed actually supplies the required fields.
- Optional **OpenAI filing analyst** using the Responses API and `OPENAI_API_KEY` from environment/GitHub Secrets only.
- `.env.example`, `.gitignore`, separate quarterly 13F workflow and v5 data-source documentation.

### AI key handling
Never put a real API key into the repository. Set `OPENAI_API_KEY` locally or create a GitHub Actions repository secret named `OPENAI_API_KEY`.
The analyzer defaults to `gpt-5-mini`; override with `OPENAI_MODEL`.

### Run
```bash
python -m src.build_snapshot --output web/latest.json --signal-log data/output/signal_log.json --with-sec
python scripts/enrich_v5.py --snapshot web/latest.json --top 80 --with-finra --with-macro
```
## v6 additions

- **Reverse DCF**: back-solves the 5-year constant revenue-growth rate implied by current enterprise value. Assumptions are explicit.
- **Revision Pulse**: Yahoo/yfinance EPS trend (current vs 30/90 days ago), revision counts and earnings surprise history.
- **Catalyst Timeline**: earnings dates, estimate revisions, insider activity, technical changes and optional AI filing events.
- **Historical Replay**: price/volume-only point-in-time signal replay with explicit survivorship-bias and execution caveats.
- **Watch & Alert**: browser-local watchlist and in-browser alerts for READY / RS-before-price conditions.
- **Portfolio Lab**: local holdings input, sector exposure, concentration, weighted RS and weighted Strength.
- `docs/DASHBOARD_RESEARCH_V6.md` documents the design references and caveats.

### v6 enrichment
```bash
python scripts/enrich_v6.py --snapshot web/latest.json --top 80 --with-replay
```

`OPENAI_API_KEY` remains optional and is never stored in the project. It is only used by the separate filing-analysis path.
## v7 additions

- **Revision Ranking** across the snapshot, combining 30D/90D EPS estimate change, net analyst revisions and surprise history.
- **Expectation Gap**: reported revenue YoY vs reverse-DCF implied constant 5Y growth, explicitly labeled as context rather than a valuation verdict.
- **Catalyst Score** with five visible layers: Revision / Surprise / Insider / Technical / Quality.
- **Signal-specific Backtests**: RS-new-high-before-price, volume breakthrough and trend-leader proxy with 5D/20D/60D forward outcomes.
- **Portfolio Correlation Matrix** calculated from aligned snapshot returns.
- **Risk Contribution** from the covariance matrix, separate from capital weight.
- **Stress Tests**: historical COVID / 2022 / 2023-bank-stress returns when available plus simple hypothetical market/tech/rate/energy shocks.
- `docs/DASHBOARD_RESEARCH_V7.md` documents methodology and limitations.

### v7 enrichment
```bash
python scripts/enrich_v7.py --snapshot web/latest.json --backtest-top 50 --with-signal-backtest --with-stress-library
```
## v8 additions — Macro

- Full **Macro** tab instead of only a few market tickers.
- Official/free **FRED** layer for rates, inflation, growth, liquidity and credit.
- Direct **New York Fed** SOFR/EFFR reference-rate API.
- **Atlanta Fed GDPNow** public-nowcast parser.
- Expanded market tape: SPY, VIX, Treasury proxy, DXY, WTI, Gold, Copper, TLT, HYG and BTC.
- **Growth × Inflation 4-quadrant regime**.
- Six axes: Growth / Inflation / Liquidity / Credit / Rates Pressure / Funding Stress.
- **Macro Risk Score** with transparent components.
- **Sector Macro Fit** pushed down to each stock, comparison table and Screen Lab.
- Daily macro-score history stored in the snapshot.

Run after v7 enrichment:
```bash
python scripts/enrich_v8.py --snapshot web/latest.json
```

See `docs/MACRO_V8.md` for exact series and methodology.
## v9 additions — Calendar & Commodities

- Dedicated **Commodities** tab: WTI, Brent, natural gas, gasoline, heating oil, gold, silver, copper, platinum, palladium, grains and soft commodities.
- Commodity trend metrics: 1D/1W/1M/3M/12M performance, 20/50DMA state, 52W position and volatility.
- Intermarket ratios: **Brent-WTI**, **Gold/Silver**, **Copper/Gold** and commodity breadth.
- **EIA physical inventories**: crude ex-SPR, total crude, gasoline and distillates with weekly changes.
- Dedicated **Macro Calendar** tab from official Fed/BLS/BEA/EIA/Treasury/OPEC sources.
- Event importance, source, category and D-day countdown.
- High-impact event count for the next 7 and 30 days.

Run after v8:
```bash
python scripts/enrich_v9.py --snapshot web/latest.json
```

See `docs/MACRO_V9.md`.


## v10 additions — full history

- **History Explorer** with 3M / 1Y / 5Y / 10Y / MAX ranges.
- Full available **FRED macro histories**, stored per series.
- Max available **commodity futures histories** and derived Brent-WTI / Gold-Silver / Copper-Gold series.
- Full **EIA petroleum inventory histories**.
- Historical **SPY / VIX / USD / rates / credit / BTC** market proxies.
- Historical **BLS/FOMC calendar archive** plus current BEA schedule.
- Click any Macro / Commodity / EIA card to open its history.
- Overlay comparison is normalized to 100 to avoid deceptive mixed-unit dual axes.
- Clear warning that normal FRED history is latest revised history, not point-in-time vintage data.

Build the historical database after the normal daily enrichments:
```bash
python scripts/build_history_v10.py --snapshot web/latest.json --history-root web/history
```

See `docs/HISTORY_V10.md`.

## v11 — Terminal UI + broader official history

- Rebuilt navigation as a grouped left-side terminal sidebar while keeping many separate feature tabs.
- `Today` is now the landing dashboard with regime, macro risk, breadth, credit, event risk, stock signals and sector leadership.
- Added dedicated tabs for **Rates, Inflation, Growth & Labor, Liquidity, Credit, FX, Housing, Energy, Metals and Agriculture**.
- Every focused metric card links to the shared full-history explorer.
- Added a global command/search bar and compact-density toggle.
- Added **Data Health** for provider provenance, historical-series count and observation coverage.
- Expanded the official FRED history registry with additional Treasury, real-yield, breakeven, credit-stress, labor, housing, FX and EIA spot-energy series.
- The existing daily GitHub Action backfills the added official series on the next connected build.

See `docs/UI_V11.md`.
