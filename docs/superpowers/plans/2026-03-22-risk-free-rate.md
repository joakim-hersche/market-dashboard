# Risk-Free Rate Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a cumulative risk-free return line (10Y government bonds) on the comparison chart, and use actual rates for Sharpe ratio and beta calculations.

**Architecture:** New `src/risk_free.py` module fetches daily 10Y yields from FRED (USD), Riksbank (EUR/GBP/SEK), and SNB (CHF). Yields are compounded into cumulative returns for chart display. `compute_analytics` is updated to use real rates for Sharpe and currency-specific benchmarks for beta.

**Tech Stack:** Python requests, pandas, FRED API, Riksbank REST API, SNB CSV API

**Spec:** `docs/superpowers/specs/2026-03-22-risk-free-rate-design.md`

---

### Task 1: Add cache + create `src/risk_free.py` with FRED fetcher (USD)

**Files:**
- Modify: `src/cache.py:27` — add `long_cache_risk_free`
- Create: `src/risk_free.py`
- Create: `tests/test_risk_free.py`

- [ ] **Step 1: Add cache entry**

In `src/cache.py`, add after line 27:

```python
long_cache_risk_free = TTLCache(maxsize=64, ttl=86400)
```

- [ ] **Step 2: Write failing tests for FRED fetcher**

```python
# tests/test_risk_free.py
import os
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from src.risk_free import fetch_risk_free_yields, _fetch_fred


class TestFetchFred:
    """FRED API fetcher for USD 10Y Treasury yield."""

    def test_returns_series_on_success(self):
        mock_json = {
            "observations": [
                {"date": "2025-01-02", "value": "4.25"},
                {"date": "2025-01-03", "value": "4.30"},
                {"date": "2025-01-06", "value": "."},   # missing
                {"date": "2025-01-07", "value": "4.28"},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_json
        mock_resp.raise_for_status = MagicMock()

        with patch("src.risk_free.requests.get", return_value=mock_resp):
            with patch.dict(os.environ, {"FRED_API_KEY": "test_key"}):
                result = _fetch_fred("2025-01-02", "2025-01-07")

        assert isinstance(result, pd.Series)
        assert len(result) == 3  # "." row dropped
        assert result.iloc[0] == pytest.approx(4.25)

    def test_returns_empty_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("FRED_API_KEY", None)
            result = _fetch_fred("2025-01-02", "2025-01-07")
        assert result.empty


class TestFetchRiskFreeYields:
    """Public dispatch function."""

    def test_usd_dispatches_to_fred(self):
        fake = pd.Series([4.0, 4.1], index=pd.to_datetime(["2025-01-02", "2025-01-03"]))
        with patch("src.risk_free._fetch_fred", return_value=fake):
            result = fetch_risk_free_yields("USD", "2025-01-02", "2025-01-03")
        assert len(result) == 2

    def test_unsupported_currency_returns_empty(self):
        result = fetch_risk_free_yields("JPY", "2025-01-02", "2025-01-03")
        assert result.empty
```

- [ ] **Step 3: Run tests — expect FAIL (module not found)**

Run: `python -m pytest tests/test_risk_free.py -v`

- [ ] **Step 4: Implement `src/risk_free.py` with FRED fetcher**

```python
"""Fetch historical 10-year government bond yields by currency.

Sources:
- USD: FRED API (DGS10) — requires FRED_API_KEY env var
- EUR: Riksbank API (DEGVB10Y, German Bund)
- GBP: Riksbank API (GBGVB10Y, UK Gilt)
- SEK: Riksbank API (SEGVB10YC)
- CHF: SNB API (rendoblid 10Y Confederation bond)
"""

import logging
import os

import pandas as pd
import requests
from cachetools import cached

from src.cache import long_cache_risk_free

_log = logging.getLogger(__name__)

# ── Currency → fetcher dispatch ──────────────────────────────────────

_RISK_FREE_LABEL = {
    "USD": "10Y Treasury",
    "EUR": "10Y Bund",
    "GBP": "10Y Gilt",
    "CHF": "10Y Confed.",
    "SEK": "10Y Gov. Bond",
}

_RIKSBANK_SERIES = {
    "EUR": "DEGVB10Y",
    "GBP": "GBGVB10Y",
    "SEK": "SEGVB10YC",
}


def risk_free_label(currency: str) -> str:
    """Human-readable label for the risk-free instrument."""
    return _RISK_FREE_LABEL.get(currency, "10Y Bond")


@cached(long_cache_risk_free)
def fetch_risk_free_yields(currency: str, start: str, end: str) -> pd.Series:
    """Return daily 10Y government bond yields (annualized %) for currency.

    Returns empty Series if the API is unavailable or the currency is
    unsupported. Values are forward-filled across weekends/holidays.
    """
    try:
        if currency == "USD":
            raw = _fetch_fred(start, end)
        elif currency in _RIKSBANK_SERIES:
            raw = _fetch_riksbank(currency, start, end)
        elif currency == "CHF":
            raw = _fetch_snb(start, end)
        else:
            return pd.Series(dtype=float)

        if raw.empty:
            return raw

        # Forward-fill weekends/holidays, then drop leading NaNs
        full_range = pd.date_range(start=raw.index.min(), end=raw.index.max(), freq="D")
        filled = raw.reindex(full_range).ffill().dropna()
        filled.index.name = "Date"
        return filled

    except Exception as exc:
        _log.warning("Risk-free fetch failed for %s: %s", currency, exc)
        return pd.Series(dtype=float)


# ── FRED (USD) ───────────────────────────────────────────────────────

def _fetch_fred(start: str, end: str) -> pd.Series:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        _log.debug("FRED_API_KEY not set — risk-free rate unavailable for USD")
        return pd.Series(dtype=float)

    resp = requests.get(
        "https://api.fred.stlouisfed.org/series/observations",
        params={
            "series_id": "DGS10",
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
        },
        timeout=15,
    )
    resp.raise_for_status()

    rows = resp.json().get("observations", [])
    data = [(r["date"], float(r["value"])) for r in rows if r["value"] != "."]
    if not data:
        return pd.Series(dtype=float)

    dates, values = zip(*data)
    return pd.Series(values, index=pd.to_datetime(dates), dtype=float)
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `python -m pytest tests/test_risk_free.py -v`

- [ ] **Step 6: Commit**

```bash
git add src/cache.py src/risk_free.py tests/test_risk_free.py
git commit -m "feat: add risk_free module with FRED fetcher for USD 10Y yields"
```

---

### Task 2: Add Riksbank fetcher (EUR, GBP, SEK)

**Files:**
- Modify: `src/risk_free.py`
- Modify: `tests/test_risk_free.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_risk_free.py`:

```python
class TestFetchRiksbank:
    """Riksbank API fetcher for EUR/GBP/SEK 10Y yields."""

    def test_returns_series_on_success(self):
        mock_json = [
            {"date": "2025-01-02", "value": 2.35},
            {"date": "2025-01-03", "value": 2.40},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_json
        mock_resp.raise_for_status = MagicMock()

        with patch("src.risk_free.requests.get", return_value=mock_resp):
            result = _fetch_riksbank("EUR", "2025-01-02", "2025-01-03")

        assert isinstance(result, pd.Series)
        assert len(result) == 2
        assert result.iloc[0] == pytest.approx(2.35)

    def test_returns_empty_on_error(self):
        with patch("src.risk_free.requests.get", side_effect=Exception("timeout")):
            result = _fetch_riksbank("EUR", "2025-01-02", "2025-01-03")
        assert result.empty
```

Also update import: `from src.risk_free import fetch_risk_free_yields, _fetch_fred, _fetch_riksbank`

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_risk_free.py::TestFetchRiksbank -v`

- [ ] **Step 3: Implement Riksbank fetcher**

Add to `src/risk_free.py`:

```python
# ── Riksbank (EUR, GBP, SEK) ────────────────────────────────────────

def _fetch_riksbank(currency: str, start: str, end: str) -> pd.Series:
    series_id = _RIKSBANK_SERIES.get(currency)
    if not series_id:
        return pd.Series(dtype=float)

    resp = requests.get(
        f"https://api.riksbank.se/swea/v1/Observations/{series_id}/{start}/{end}",
        timeout=15,
    )
    resp.raise_for_status()

    rows = resp.json()
    if not rows:
        return pd.Series(dtype=float)

    data = [(r["date"], float(r["value"])) for r in rows if r.get("value") is not None]
    if not data:
        return pd.Series(dtype=float)

    dates, values = zip(*data)
    return pd.Series(values, index=pd.to_datetime(dates), dtype=float)
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_risk_free.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/risk_free.py tests/test_risk_free.py
git commit -m "feat: add Riksbank fetcher for EUR/GBP/SEK 10Y bond yields"
```

---

### Task 3: Add SNB fetcher (CHF)

**Files:**
- Modify: `src/risk_free.py`
- Modify: `tests/test_risk_free.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_risk_free.py`:

```python
class TestFetchSnb:
    """SNB API fetcher for CHF 10Y Confederation bond yield."""

    def test_returns_series_on_success(self):
        csv_content = (
            "Date;Value\n"
            "2025-01-02;0.45\n"
            "2025-01-03;0.48\n"
        )
        mock_resp = MagicMock()
        mock_resp.text = csv_content
        mock_resp.raise_for_status = MagicMock()

        with patch("src.risk_free.requests.get", return_value=mock_resp):
            result = _fetch_snb("2025-01-02", "2025-01-03")

        assert isinstance(result, pd.Series)
        assert len(result) == 2

    def test_returns_empty_on_error(self):
        with patch("src.risk_free.requests.get", side_effect=Exception("timeout")):
            result = _fetch_snb("2025-01-02", "2025-01-03")
        assert result.empty
```

Also update import: `from src.risk_free import fetch_risk_free_yields, _fetch_fred, _fetch_riksbank, _fetch_snb`

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_risk_free.py::TestFetchSnb -v`

- [ ] **Step 3: Implement SNB fetcher**

The SNB CSV format needs investigation — the exact column names and delimiter need to be confirmed from a real response. The implementation should:

```python
# ── SNB (CHF) ────────────────────────────────────────────────────────

def _fetch_snb(start: str, end: str) -> pd.Series:
    resp = requests.get(
        "https://data.snb.ch/api/cube/rendoblid/data/csv/en",
        params={"dimSel": "D0(10J0)", "fromDate": start, "toDate": end},
        timeout=15,
    )
    resp.raise_for_status()

    # SNB CSV uses semicolons. Parse and extract date + value columns.
    # The exact column layout may vary — read all, find the date and numeric columns.
    from io import StringIO
    df = pd.read_csv(StringIO(resp.text), sep=";")

    # SNB typically returns columns like: Date;Value or Date;D0;Value
    # Find the date column and the numeric value column
    date_col = [c for c in df.columns if "date" in c.lower() or "datum" in c.lower()]
    val_col = [c for c in df.columns if "value" in c.lower() or c.startswith("D0") or df[c].dtype in ("float64", "object")]

    if not date_col:
        # Fallback: assume first column is date, last is value
        date_col = [df.columns[0]]
        val_col = [df.columns[-1]]

    dates = pd.to_datetime(df[date_col[0]])
    values = pd.to_numeric(df[val_col[-1]], errors="coerce")

    series = pd.Series(values.values, index=dates, dtype=float).dropna()
    return series
```

**Note:** The SNB CSV format must be verified against a real API call during testing. The test mocks a simplified version, but the implementation should handle the actual format. When running locally, verify with:
```bash
curl "https://data.snb.ch/api/cube/rendoblid/data/csv/en?dimSel=D0(10J0)&fromDate=2024-01-01&toDate=2024-03-01"
```
Adjust column parsing if needed.

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_risk_free.py -v`

- [ ] **Step 5: Verify SNB format with live call and adjust if needed**

Run a manual curl to check the actual CSV structure:
```bash
curl -s "https://data.snb.ch/api/cube/rendoblid/data/csv/en?dimSel=D0(10J0)&fromDate=2024-01-01&toDate=2024-03-01" | head -5
```
Update `_fetch_snb` parsing and test mock if the format differs.

- [ ] **Step 6: Commit**

```bash
git add src/risk_free.py tests/test_risk_free.py
git commit -m "feat: add SNB fetcher for CHF 10Y Confederation bond yield"
```

---

### Task 4: Add risk-free line to comparison chart

**Files:**
- Modify: `src/ui/overview.py:537` — add toggle
- Modify: `src/ui/overview.py:585-693` — fetch + render risk-free line

- [ ] **Step 1: Add the risk-free toggle switch**

In `src/ui/overview.py`, after line 537 (the bench_switch line), add:

```python
rf_switch = ui.switch("Risk-free", value=False).style(f"font-size:12px;color:{TEXT_MUTED};")
```

- [ ] **Step 2: Add import at top of file**

Add to the imports section:

```python
from src.risk_free import fetch_risk_free_yields, risk_free_label
```

- [ ] **Step 3: Fetch risk-free data in `_fetch_comparison_data`**

In `_fetch_comparison_data()` (around line 592), after the benchmark fetch block (line 652), add:

```python
# Fetch risk-free yield curve if requested
rf_cumulative = None
rf_label = None
show_rf = rf_switch.value
if show_rf:
    rf_label = f"Risk-Free ({risk_free_label(base_currency)})"
    # Determine date range from comparison data
    try:
        all_series = [s for s in data.values() if s is not None and not s.empty]
        if all_series:
            rf_start = str(min(s.index.min() for s in all_series).date())
            rf_end = str(max(s.index.max() for s in all_series).date())
            yields = fetch_risk_free_yields(base_currency, rf_start, rf_end)
            if not yields.empty:
                daily_rate = (1 + yields / 100) ** (1 / 365) - 1
                rf_cumulative = (1 + daily_rate).cumprod() * 100
    except Exception:
        pass
```

Update the return statement to include risk-free data:

```python
return data, bench_series, bench_name, rf_cumulative, rf_label
```

- [ ] **Step 4: Update caller to unpack new return values**

Change line 656 from:
```python
comparison_data, bench_series, bench_name = await run.io_bound(_fetch_comparison_data)
```
To:
```python
comparison_data, bench_series, bench_name, rf_cumulative, rf_label = await run.io_bound(_fetch_comparison_data)
```

- [ ] **Step 5: Add risk-free trace to chart**

After the benchmark overlay block (after line 678), add:

```python
# Add risk-free rate overlay
if rf_switch.value and rf_cumulative is not None and not rf_cumulative.empty:
    import plotly.graph_objects as go
    fig.add_trace(go.Scatter(
        x=rf_cumulative.index, y=rf_cumulative.values,
        mode="lines", name=rf_label,
        line=dict(color="#10B981", width=2, dash="dash"),
        hovertemplate=f"{rf_label}: %{{y:.1f}}<extra></extra>",
    ))
```

- [ ] **Step 6: Register debounce on rf_switch**

After line 715 (`bench_switch.on_value_change(_debounced_update)`), add:

```python
rf_switch.on_value_change(_debounced_update)
```

- [ ] **Step 7: Test manually — toggle risk-free on comparison chart**

Start app, open comparison chart, toggle "Risk-free" switch. Verify:
- Dashed green line appears, rebased to ~100 at start
- Label shows currency-specific bond name
- Hover shows value
- No errors when toggling on/off rapidly

- [ ] **Step 8: Commit**

```bash
git add src/ui/overview.py
git commit -m "feat: add risk-free rate line to comparison chart"
```

---

### Task 5: Dynamic Sharpe ratio + currency-specific beta

**Files:**
- Modify: `src/portfolio.py:14-67`
- Modify: `src/ui/health.py:1194-1197` — pass `base_currency`
- Modify: `src/ui/overview.py:748-750` — pass `base_currency` in Excel export
- Modify: `tests/test_portfolio.py` — update tests

- [ ] **Step 1: Update `compute_analytics` signature and implementation**

In `src/portfolio.py`, replace the `compute_analytics` function (lines 14-67):

```python
def compute_analytics(
    portfolio: dict,
    price_data: dict,
    bench_data: pd.DataFrame,
    base_currency: str = "USD",
) -> pd.DataFrame:
    """
    Compute per-ticker risk analytics from 1-year price history.
    price_data: {ticker: DataFrame with 'Close' column}
    bench_data: DataFrame with 'Close' column (currency-specific benchmark)
    base_currency: user's base currency (for risk-free rate + benchmark selection)
    Returns DataFrame with columns: Ticker, Volatility, Max Drawdown, Sharpe Ratio, Beta
    """
    from src.risk_free import fetch_risk_free_yields

    # Dynamic risk-free rate from 10Y government bonds
    try:
        end_date = str(pd.Timestamp.today().date())
        start_date = str((pd.Timestamp.today() - pd.DateOffset(years=1)).date())
        yields = fetch_risk_free_yields(base_currency, start_date, end_date)
        if not yields.empty:
            avg_annual_rf = yields.mean() / 100
        else:
            avg_annual_rf = 0.04  # fallback
    except Exception:
        avg_annual_rf = 0.04

    bench_returns = pd.Series(dtype=float)
    if not bench_data.empty and "Close" in bench_data.columns:
        bench_returns = bench_data["Close"].pct_change().dropna()

    rows = []
    for ticker in portfolio:
        hist = price_data.get(ticker)
        if hist is None or hist.empty or "Close" not in hist.columns:
            continue
        prices = hist["Close"].dropna()
        if len(prices) < 30:
            continue

        daily_returns = prices.pct_change().dropna()

        # Annualised volatility
        volatility = daily_returns.std() * (252 ** 0.5)

        # Max drawdown
        rolling_max = prices.cummax()
        drawdown = (prices - rolling_max) / rolling_max
        max_drawdown = float(drawdown.min())

        # Sharpe ratio (annualised, dynamic risk-free rate)
        daily_rf = avg_annual_rf / 252
        excess = daily_returns - daily_rf
        sharpe = float((excess.mean() / excess.std()) * (252 ** 0.5)) if excess.std() > 0 else None

        # Beta vs currency-specific benchmark
        beta = None
        if not bench_returns.empty:
            aligned = pd.concat([daily_returns, bench_returns], axis=1, join="inner").dropna()
            aligned.columns = ["stock", "bench"]
            if len(aligned) >= 30 and aligned["bench"].var() > 0:
                beta = float(aligned["stock"].cov(aligned["bench"]) / aligned["bench"].var())

        rows.append({
            "Ticker":       ticker,
            "Volatility":   round(volatility * 100, 1),
            "Max Drawdown": round(max_drawdown * 100, 1),
            "Sharpe Ratio": round(sharpe, 2) if sharpe is not None else None,
            "Beta":         round(beta, 2) if beta is not None else None,
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()
```

- [ ] **Step 2: Update callers — health.py**

In `src/ui/health.py` around line 1189-1197, the benchmark data fetch currently fetches SPY. Change it to use the currency-specific benchmark:

Find the block that fetches SPY data and replace with:

```python
_BENCH_MAP = {
    "USD": "SPY",
    "CHF": "^SSMI",
    "EUR": "^STOXX50E",
    "GBP": "^FTSE",
    "SEK": "^OMX",
}
bench_ticker = _BENCH_MAP.get(currency, "SPY")
bench_data = fetch_analytics_history(bench_ticker)
```

Update the `compute_analytics` call:

```python
analytics_df = compute_analytics(portfolio, price_data_1y, bench_data, currency)
```

- [ ] **Step 3: Update callers — overview.py Excel export**

In `src/ui/overview.py` around line 748-750, same pattern — replace SPY with currency-specific benchmark and pass `base_currency`:

```python
bench_ticker = {"USD": "SPY", "CHF": "^SSMI", "EUR": "^STOXX50E", "GBP": "^FTSE", "SEK": "^OMX"}.get(currency, "SPY")
bench_data = fetch_analytics_history(bench_ticker)
analytics_df = compute_analytics(portfolio, price_data_1y, bench_data, currency)
```

- [ ] **Step 4: Update tests**

In `tests/test_portfolio.py`, update any calls to `compute_analytics` to match the new signature (adding `base_currency` parameter). The old `spy_data` parameter is now `bench_data`.

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/ -v`

- [ ] **Step 6: Commit**

```bash
git add src/portfolio.py src/ui/health.py src/ui/overview.py tests/test_portfolio.py
git commit -m "feat: dynamic Sharpe ratio from real yields, currency-specific beta"
```

---

### Task 6: Update Guide tab

**Files:**
- Modify: `src/ui/guide.py:84-95`

- [ ] **Step 1: Update Risk Metrics section and add Risk-Free Rate section**

In `src/ui/guide.py`, replace the "Risk Metrics" section (lines 84-95) with:

```python
        with ui.element("div").classes("chart-card w-full").style("overflow-x:auto;"):
            ui.label("Risk Metrics (in Detailed Metrics)").classes("text-lg font-bold").style(f"color:{TEXT_PRIMARY}")
            ui.markdown("""These are standard measures used by professional investors, now inside the collapsible \
"Detailed Metrics" section of the Portfolio Health tab:

- **Volatility** — how much the price swings day to day, expressed as a yearly percentage. Higher = more unpredictable.
- **Worst Drop (Max Drawdown)** — the biggest peak-to-trough fall in the past year.
- **Return/Risk Score (Sharpe Ratio)** — how much return you earn per unit of risk. Uses the actual 10-year \
government bond yield for your currency as the risk-free rate (not a fixed assumption). Above 1 is good, above 2 is excellent.
- **Market Sensitivity (Beta)** — how much the stock moves relative to your local market benchmark \
(S&P 500 for USD, SMI for CHF, Euro Stoxx 50 for EUR, FTSE 100 for GBP, OMX 30 for SEK).
- **Correlation** — whether two stocks tend to go up and down together (close to 1.0) or move independently (close to 0).
- **P/E Ratio** — how many years of current earnings you are paying for.
- **Dividend Yield** — the annual dividend payment as a percentage of the stock price.""").classes("text-sm").style(f"color:{TEXT_SECONDARY}")

        with ui.element("div").classes("chart-card w-full").style("overflow-x:auto;"):
            ui.label("Risk-Free Rate Line").classes("text-lg font-bold").style(f"color:{TEXT_PRIMARY}")
            ui.markdown("""The "Risk-free" toggle on the Portfolio Comparison chart shows what your money would have \
earned in 10-year government bonds — the standard proxy for a risk-free return:

| Currency | Bond used |
|----------|-----------|
| USD | US 10-Year Treasury |
| EUR | German 10-Year Bund |
| GBP | UK 10-Year Gilt |
| CHF | Swiss 10-Year Confederation Bond |
| SEK | Swedish 10-Year Government Bond |

**Why the German Bund for EUR?** Germany has the highest credit rating in the eurozone, and the Bund is the \
industry-standard risk-free benchmark for euro-denominated assets. Other eurozone countries (Italy, Spain, etc.) \
carry additional credit risk, which means their higher yields are not truly "risk-free."

The line compounds daily yields into a cumulative return, rebased to 100 like all other lines on the chart. \
A flat or gently rising line means rates were low; a steeper climb means bonds were paying more.

This feature requires a free FRED API key for USD (set `FRED_API_KEY` in your environment). EUR, GBP, CHF, and \
SEK data is fetched from central bank APIs with no key required.""").classes("text-sm").style(f"color:{TEXT_SECONDARY}")
```

- [ ] **Step 2: Verify guide renders correctly**

Start app, navigate to Guide tab, check the two new/updated sections render properly with the table.

- [ ] **Step 3: Commit**

```bash
git add src/ui/guide.py
git commit -m "docs: add risk-free rate explanation to guide tab"
```

---

### Task 7: End-to-end verification

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`

- [ ] **Step 2: Manual verification checklist**

Start the app and verify:

1. **Comparison chart**: toggle "Risk-free" — green dashed line appears
2. **Label**: correct bond name for selected currency
3. **Hover**: shows cumulative value on hover
4. **Benchmark + Risk-free together**: both lines visible simultaneously
5. **Time ranges**: risk-free line updates when switching 3M/6M/1Y/Max
6. **Health tab**: Sharpe ratio values changed from fixed-4% calculation
7. **Health tab**: Beta column header or tooltip reflects local benchmark
8. **Guide tab**: new "Risk-Free Rate Line" section visible with table
9. **No FRED key**: risk-free toggle hidden (or no line appears) for USD
10. **Non-USD currency**: risk-free works without any API key (Riksbank/SNB)

- [ ] **Step 3: Final commit if any fixes needed**
