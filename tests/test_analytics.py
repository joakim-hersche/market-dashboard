import numpy as np
import pandas as pd
from unittest.mock import patch

from src.portfolio import compute_analytics


def test_sortino_ratio_computed():
    """Sortino ratio should appear in analytics output."""
    dates = pd.bdate_range("2024-01-01", periods=60)
    prices = pd.DataFrame({"Close": 100 + np.cumsum(np.random.randn(60) * 0.5)}, index=dates)

    portfolio = {"TEST": [{"shares": 10}]}
    price_data = {"TEST": prices}
    bench_data = prices.copy()

    with patch("src.risk_free.fetch_risk_free_yields", return_value=pd.Series(dtype=float)):
        result = compute_analytics(portfolio, price_data, bench_data, "USD")

    assert "Sortino Ratio" in result.columns
    assert result.iloc[0]["Sortino Ratio"] is not None
