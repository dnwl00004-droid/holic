# Macro v9 — Calendar + Commodities

## What changed
v8 described the macro *state*. v9 adds the macro *clock* and the physical/commodity tape.

### Macro event calendar
Official-source event layer:
- Federal Reserve — FOMC policy decisions
- BLS — CPI, Employment Situation, PPI, JOLTS, ECI, import/export prices
- BEA — GDP, Personal Income & Outlays/PCE, trade
- EIA — Weekly Petroleum Status Report
- U.S. Treasury — tentative auction schedule where the current quarterly XML can be discovered
- OPEC — current official meeting dates from press releases

Every event stores date, ET time when available, category, source, importance and D-day.
The UI can filter All / High Impact / Economic / Central Bank / Energy / OPEC / Treasury.

## Commodity board
Yahoo/yfinance futures are grouped into:

**Energy**
WTI, Brent, Henry Hub natural gas, RBOB gasoline, heating oil.

**Metals**
Gold, silver, copper, platinum, palladium and optional iron ore when the provider exposes it.

**Agriculture**
Corn, wheat, soybeans, coffee, cocoa, sugar, cotton and live cattle.

For each contract:
- 1D / 1W / 1M / 3M / 12M return
- 20DMA / 50DMA state
- 52-week range position
- 20-day annualized volatility
- 120-session chart history

Derived intermarket measures:
- Brent minus WTI spread
- Gold/Silver ratio
- Copper/Gold ratio
- commodity breadth (% above 50DMA and % positive over 1M)

## Physical oil-market data
EIA weekly inventory pages are read directly for:
- crude oil excluding SPR
- total crude oil
- total gasoline
- distillate fuel oil

The dashboard shows the latest level, weekly change and position relative to recent averages.

## Important caveats
- Futures returns can be affected by contract rolls.
- EIA release dates can shift around U.S. holidays.
- OPEC can change meeting timing through later press releases.
- Treasury auction schedules are tentative.
- Calendar importance is an internal classification, not an expected-volatility forecast.
