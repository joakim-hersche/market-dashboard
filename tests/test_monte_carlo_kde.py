import numpy as np

from src.monte_carlo import _simulate_paths


def test_simulation_produces_valid_paths():
    """Cholesky simulation should produce portfolio paths with correct shape."""
    N = 3
    mean_log = np.array([0.0005, 0.0003, 0.0004])
    cov_log = np.eye(N) * 0.0001
    start_prices = np.array([100.0, 50.0, 200.0])
    shares = np.array([10, 20, 5])
    rng = np.random.default_rng(42)

    portfolio_paths, ticker_paths = _simulate_paths(
        mean_log, cov_log, start_prices, shares,
        n_sims=100, horizon_days=10, rng=rng,
    )

    assert portfolio_paths.shape == (100, 10)
    assert ticker_paths.shape == (100, 10, 3)
    assert np.all(portfolio_paths > 0)


def test_degenerate_covariance_fallback():
    """Non-positive-definite covariance should fall back to diagonal without error."""
    N = 2
    mean_log = np.array([0.0005, 0.0003])
    # Deliberately singular covariance
    cov_log = np.array([[0.0001, 0.0001], [0.0001, 0.0001]])
    start_prices = np.array([100.0, 50.0])
    shares = np.array([10, 20])
    rng = np.random.default_rng(42)

    portfolio_paths, ticker_paths = _simulate_paths(
        mean_log, cov_log, start_prices, shares,
        n_sims=50, horizon_days=5, rng=rng,
    )

    assert portfolio_paths.shape == (50, 5)
    assert np.all(portfolio_paths > 0)
