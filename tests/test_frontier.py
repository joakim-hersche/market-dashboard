import numpy as np
import pandas as pd
import pytest

from src.frontier import compute_efficient_frontier, portfolio_position


def test_frontier_returns_expected_structure():
    """Frontier should return frontier points and stock positions."""
    np.random.seed(42)
    dates = pd.bdate_range("2024-01-01", periods=252)
    returns = pd.DataFrame({
        "A": np.random.randn(252) * 0.02 + 0.001,
        "B": np.random.randn(252) * 0.01 + 0.0005,
        "C": np.random.randn(252) * 0.015 + 0.0008,
    }, index=dates)

    result = compute_efficient_frontier(returns, n_points=10)

    assert "frontier" in result
    assert "stocks" in result
    assert len(result["frontier"]) > 0
    assert len(result["stocks"]) == 3
    for cvar, ret in result["frontier"]:
        assert isinstance(cvar, float)
        assert isinstance(ret, float)


def test_portfolio_position():
    """Should return (cvar, return) for given weights."""
    np.random.seed(42)
    dates = pd.bdate_range("2024-01-01", periods=252)
    returns = pd.DataFrame({
        "A": np.random.randn(252) * 0.02 + 0.001,
        "B": np.random.randn(252) * 0.01 + 0.0005,
    }, index=dates)

    weights = {"A": 0.6, "B": 0.4}
    cvar, ret = portfolio_position(returns, weights)

    assert isinstance(cvar, float)
    assert isinstance(ret, float)
    assert cvar > 0


def test_frontier_with_too_few_stocks():
    """Should return empty result with fewer than 3 stocks."""
    dates = pd.bdate_range("2024-01-01", periods=252)
    returns = pd.DataFrame({
        "A": np.random.randn(252) * 0.02,
    }, index=dates)

    result = compute_efficient_frontier(returns)
    assert result["frontier"] == []
