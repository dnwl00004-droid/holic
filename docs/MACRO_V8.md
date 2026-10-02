# Macro v8

## Data layer

### FRED — public CSV endpoints
**Rates**
- DFF — Effective Federal Funds Rate
- DGS2 — 2Y Treasury
- DGS10 — 10Y Treasury
- DGS30 — 30Y Treasury
- T10Y2Y — 10Y minus 2Y curve
- T10Y3M — 10Y minus 3M curve
- DFII10 — 10Y real yield
- T10YIE — 10Y breakeven inflation

**Inflation**
- CPIAUCSL — headline CPI, transformed to YoY
- CPILFESL — core CPI, transformed to YoY
- PCEPILFE — core PCE, transformed to YoY

**Growth / labor**
- UNRATE — unemployment rate
- PAYEMS — 3-month payroll level change
- INDPRO — industrial production YoY
- RSAFS — retail sales YoY
- HOUST — housing starts YoY

**Liquidity**
- WALCL — Federal Reserve total assets
- RRPONTSYD — overnight reverse repo
- WRESBAL — reserve balances
- WTREGEN — Treasury General Account
- M2SL — M2 YoY

**Credit**
- BAMLH0A0HYM2 — US high-yield OAS
- BAMLC0A0CM — broad US corporate OAS

### New York Fed
Direct reference-rate API:
- SOFR
- EFFR
- SOFR minus EFFR basis

### Atlanta Fed
The public GDPNow commentary is parsed conservatively. If page wording changes, the adapter returns unavailable instead of inventing a value.

### Yahoo market proxies
SPY / VIX / 10Y proxy / DXY / WTI / Gold / Copper / TLT / HYG / BTC.

## Regime model
Six transparent axes:
1. Growth
2. Inflation pressure
3. Liquidity
4. Credit health
5. Rates pressure
6. Funding stress

Growth × Inflation quadrant:
- GOLDILOCKS
- REFLATION
- STAGFLATION
- DISINFLATION_SLOWDOWN

`macro_risk_score` combines rates pressure, weak credit, weak liquidity, weak growth and funding stress.

## Stock integration
Each sector has an explicit sensitivity vector to Growth / Inflation / Liquidity / Credit / Rates Pressure.
Every stock receives a `Macro Fit` score from its sector.

This is descriptive context, not a return forecast. The score is visible in:
- stock detail / Why this stock?
- comparison table
- Macro sector ranking
- Screen Lab (`macro tailwind`, `매크로 순풍`, `macro headwind`, `매크로 역풍`)
