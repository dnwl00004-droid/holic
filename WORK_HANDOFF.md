# RS Radar — 2026-10-02 resume

Repository: https://github.com/dnwl00004-droid/holic

Restored the verified v14 archive from 2026-10-01. The repository previously
contained only a README. Data remains genuine: 58 FRED series, eight EIA series,
335,000 saved observations, and 444 official calendar events.

## This change

- Split initial validation/Pages publishing from the long provider refresh.
- Added a real Chromium check of all 49 routes at 1440px and 390px, plus
  historical-series loading. CI preserves screenshots as `browser-evidence`.
- Refresh continues on weekdays at 22:30 UTC, preserves last verified data,
  and triggers publishing only after a successful refresh.
- No paid API or OpenAI call is required by either default workflow.

## Verified locally

- Python: 31 tests passed.
- JavaScript syntax and DOM contracts: passed, 49 routes in four scenarios.
- Published data: 66 histories, 335,000 observations, no duplicate HTML IDs.
- A fresh SPY request with yfinance 1.7.0 still returned a rate-limit error.
  Stocks and unavailable futures therefore remain N/A.
- Local Chromium download was blocked; actual browser checks run in Actions.

## Deployment activation

Repository Settings → Pages → Build and deployment → Source → GitHub Actions.
Then run the `Validate and deploy dashboard` workflow. Until that setting is
enabled and the deploy job passes, https://dnwl00004-droid.github.io/holic/
is an intended address, not a confirmed working deployment.

## Optional secrets

`SEC_USER_AGENT`: a real application/contact identifier for SEC enrichment.
FRED and EIA public endpoints used by this project require no paid key.
`OPENAI_API_KEY` is optional for the separate filing-analysis example, and is
not read by the default refresh or deployment workflow.

## Remaining limitations

- Equity/universe pricing and all dependent stock analytics need a working
  provider; do not replace missing values with illustrative numbers.
- Forecast/actual/surprise calendar fields and several research feeds remain
  unconnected.
- Revised historical FRED values are not point-in-time vintage observations.
- Confirm Actions browser evidence and the actual deployment before declaring
  the dashboard live.
