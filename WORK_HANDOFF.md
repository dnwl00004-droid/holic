# RS Radar — resumed 2026-10-03

Repository: https://github.com/dnwl00004-droid/holic
Live dashboard: https://dnwl00004-droid.github.io/holic/

GitHub Pages uses GitHub Actions. Deployment succeeded and the public dashboard
was opened and verified after repository-owner authentication.

## Current changes

- Restored the verified v14 archive, including 58 FRED and eight EIA histories,
  335,000 saved observations and 444 official calendar events.
- v15 adds validated Nasdaq daily OHLCV for equities and SPY, plus 14
  commodity-linked ETFs. The local build contains 496 of 503 constituents
  (98.61% coverage), aligned to the SPY observation date. Seven invalid or
  insufficient histories are excluded with reasons in Data Health.
- Nasdaq validation checks symbol identity, pagination, session dates, positive
  consistent OHLC and unexplained large discontinuities. Missing volumes remain
  missing. Price returns exclude cash dividends; ordinary dividend adjustments
  are not represented. Cached source timestamps survive failed collections.
- Actual stock data exposed VCP pivot selection, RSI and NumPy JSON errors.
  VCP now uses separate high/low pivot arrays, RSI uses Wilder smoothing, and
  trend-template results serialize as Python booleans.
- Analyst estimate collection is explicit opt-in; disconnected research inputs
  remain unavailable. Replay and signal backtests use Nasdaq quote histories.
- Split validation/publishing from the long data refresh. The weekday refresh
  runs at 22:30 UTC (07:30 KST the next day) and publishes only after validation.
- Calendar countdowns use the current Eastern date and release time. Today and
  Calendar show ET and KST, including the Korean date when it changes.
- Today includes eight official Macro Pulse indicators with observation dates,
  source status and direct full-history links. Cached regime inputs are labeled.
- Full history stays available through 200-row pages, page jumps and CSV export
  of every observation in the selected range. Chart comparisons align dates.
- Failed history loads clear the previous value/chart instead of showing a
  different series under a new title. Unverified history payloads are rejected.
- Market/futures collection runs in a bounded child process (300 seconds).
  Provider failures retain verified cached data and preserve separate macro
  collection. Data Health reports source errors, durations and cache ages.
- Four consecutive FRED transport failures stop queued requests to that shared
  endpoint for the current run. Successful responses reset the counter;
  individual missing-series errors do not stop other series.
  HTTP access/rate-limit responses stop queued calls immediately.
- Derived futures spreads/ratios store their complete same-date history. Cached
  inputs produce a stale result. Spot prices remain distinct from futures;
  copper/gold quoted-price units are explicit.
- Snapshot archives use the completed build timestamp. Multiple macro refreshes
  with the same equity date preserve separate snapshots.
- Refresh commits rebase on current main to preserve concurrent source edits.

## Validation

- 50 Python tests pass, including child timeout, failed-child restoration,
  full derived histories, safe error reporting and separate archive timestamps.
- JavaScript syntax and DOM contracts pass for 49 routes in four scenarios.
- The data validator confirms 83 available histories and over 356,000 observations,
  with no duplicate HTML IDs or invalid history references.
- Real Chromium Actions checks cover 49 routes on desktop and mobile, history
  pagination, oldest/newest observations and complete CSV export. The v15 checks
  also exercise real-stock search, quote provenance, research charts, stock CSV
  export, commodity fund units and linked histories. Screenshot
  evidence is retained as the browser-evidence workflow artifact.

## Data limitations

The dashboard has partial data. Nasdaq equity and ETF prices are available.
Yahoo-only futures, index, dollar and crypto fields remain unavailable when that
provider fails. Commodity-linked ETF prices are USD per fund share, separate
from futures and spot prices. Current observations and actual successful fetch
timestamps appear next to each source.
Official histories are retained when FRED or EIA requests fail; availability
alone does not mean the latest collection succeeded. Check Data Health and
individual observation dates.

Calendar forecasts/actuals/surprises and several research feeds remain
unconnected. Revised FRED histories are not point-in-time vintage data.
Do not add illustrative numbers to fill missing financial values.

## Optional configuration

SEC_USER_AGENT can enable SEC enrichment with a real application/contact
identifier. Public FRED and EIA collection requires no paid API key.
OPENAI_API_KEY is used only by the separate filing-analysis example, never by
the default refresh or deploy workflows.
