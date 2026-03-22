# Risk-Free Rate Integration

## Goal

Add a 10-year government bond yield line to the comparison chart, and use actual risk-free rates in Sharpe ratio and beta calculations instead of hardcoded values.

## Data Sources

| Currency | Bond | Source | Series/Endpoint |
|----------|------|--------|-----------------|
| USD | US 10Y Treasury | FRED API | `DGS10` |
| EUR | German 10Y Bund | Riksbank API | `DEGVB10Y` |
| GBP | UK 10Y Gilt | Riksbank API | `GBGVB10Y` |
| CHF | Swiss 10Y Confed. | SNB API | `rendoblid/D0(10J0)` |
| SEK | Swedish 10Y Gov. | Riksbank API | `SEGVB10YC` |

**API keys:**
- FRED: requires `FRED_API_KEY` env var (free, instant registration)
- SNB: no key needed
- Riksbank: no key needed for observation queries

All responses cached 24 hours, same TTL as other long-term data.

## New Module: `src/risk_free.py`

Single public function:

```python
def fetch_risk_free_yields(currency: str, start_date: str, end_date: str) -> pd.Series:
    """
    Return daily 10Y government bond yields (annualized %) for the given
    base currency over the requested date range.

    Falls back gracefully: returns empty Series if API unavailable or
    FRED_API_KEY missing (for USD).
    """
```

Internally dispatches to three private fetchers:

### FRED fetcher (USD)
- `GET https://api.fred.stlouisfed.org/series/observations?series_id=DGS10&api_key={key}&file_type=json&observation_start={start}&observation_end={end}`
- Parse JSON, convert to pandas Series indexed by date
- Handle `"."` values (FRED uses `"."` for missing data)

### Riksbank fetcher (EUR, GBP, SEK)
- `GET https://api.riksbank.se/swea/v1/Observations/{series_id}/{start}/{end}`
- JSON array of `{date, value}` objects
- Series IDs: `DEGVB10Y` (EUR), `GBGVB10Y` (GBP), `SEGVB10YC` (SEK)

### SNB fetcher (CHF)
- `GET https://data.snb.ch/api/cube/rendoblid/data/csv/en?dimSel=D0(10J0)&fromDate={start}&toDate={end}`
- CSV with semicolon delimiter
- Parse with pandas, extract date and value columns

### Common post-processing
All fetchers return a `pd.Series` (index=date, values=annualized yield %). The public function:
1. Forward-fills missing days (weekends, holidays)
2. Caches result in a dedicated `long_cache_risk_free` (24h TTL)

## Comparison Chart Changes

File: `src/ui/overview.py`, function `build_comparison`

### New toggle
Add a `ui.switch("Risk-free", value=False)` alongside the existing benchmark switch (line ~537). Same styling.

### New mapping
```python
_RISK_FREE_LABEL = {
    "USD": "10Y Treasury",
    "EUR": "10Y Bund",
    "GBP": "10Y Gilt",
    "CHF": "10Y Confed.",
    "SEK": "10Y Gov. Bond",
}
```

### Data flow (when toggle is on)
1. Call `fetch_risk_free_yields(base_currency, start_date, end_date)`
2. If empty Series returned, hide the toggle (API unavailable)
3. Convert annualized yield to cumulative return:
   ```python
   daily_rate = (1 + yields / 100) ** (1 / 365) - 1
   cumulative = (1 + daily_rate).cumprod() * 100
   ```
4. Add Plotly trace:
   - Dashed line, color `#10B981` (muted green)
   - Name: `"Risk-Free ({label})"` where label comes from `_RISK_FREE_LABEL`
   - Same hover template pattern as benchmark

### Visibility
Same pattern as benchmark: trace excluded from `ticker_visibility` pill toggling. Always visible when switch is on.

## Sharpe Ratio Fix

File: `src/portfolio.py`, function `compute_analytics`

Replace:
```python
RISK_FREE_RATE = 0.04
daily_rf = RISK_FREE_RATE / 252
```

With:
```python
from src.risk_free import fetch_risk_free_yields

yields = fetch_risk_free_yields(base_currency, start_date, end_date)
if yields.empty:
    avg_annual_rf = 0.04  # fallback
else:
    avg_annual_rf = yields.mean() / 100
daily_rf = avg_annual_rf / 252
```

This requires threading `base_currency` into `compute_analytics()`. Currently the function signature is `compute_analytics(ticker)` — it needs to become `compute_analytics(ticker, base_currency="USD")` with USD as fallback default.

## Beta Fix

File: `src/portfolio.py`, function `compute_analytics`

Replace hardcoded SPY with currency-specific benchmark:

```python
_BETA_BENCH = {
    "USD": "SPY",
    "CHF": "^SSMI",
    "EUR": "^STOXX50E",
    "GBP": "^FTSE",
    "SEK": "^OMX",
}
bench_ticker = _BETA_BENCH.get(base_currency, "SPY")
```

Reuse the same `_BENCH_MAP` from overview.py (extract to a shared location or duplicate the small dict).

## Guide Tab Update

File: `src/ui/guide.py`

Add a new section after "Risk Metrics" explaining:
- The risk-free rate line represents the cumulative return of holding 10-year government bonds
- For EUR, the German Bund is used as proxy — Germany has the highest eurozone credit rating and the Bund is the industry-standard EUR risk-free benchmark
- The same rates feed into Sharpe ratio calculations
- Requires `FRED_API_KEY` environment variable for USD users

## Graceful Degradation

- If `FRED_API_KEY` is not set and currency is USD: risk-free toggle hidden, Sharpe falls back to 4%
- If Riksbank/SNB API unreachable: risk-free toggle hidden, Sharpe falls back to 4%
- No error messages shown to user — feature simply not available

## Files Changed

| File | Change |
|------|--------|
| `src/risk_free.py` | **New** — fetcher module |
| `src/cache.py` | Add `long_cache_risk_free` |
| `src/ui/overview.py` | Risk-free toggle + trace on comparison chart |
| `src/portfolio.py` | Dynamic Sharpe ratio + currency-specific beta |
| `src/ui/guide.py` | Explanation section |
| `src/ui/health.py` | Pass `base_currency` to `compute_analytics()` |

## Not in Scope

- FX-adjusting the risk-free rate (it's already currency-native)
- Showing multiple EUR country yields as a range
- Historical yield curve visualization
- Duration/interest rate risk analysis
