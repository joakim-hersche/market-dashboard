"""Mean-CVaR efficient frontier computation.

Uses cvxpy to solve a series of linear programs at different risk-aversion
levels, producing the Pareto-optimal curve of (tail risk, expected return).
"""

import logging

import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)


def compute_efficient_frontier(
    returns: pd.DataFrame,
    n_points: int = 20,
    confidence: float = 0.95,
) -> dict:
    """Compute the Mean-CVaR efficient frontier.

    Parameters
    ----------
    returns : DataFrame
        Daily returns with columns = tickers.
    n_points : int
        Number of points along the frontier.
    confidence : float
        Confidence level for CVaR (e.g. 0.95).

    Returns
    -------
    dict with:
        frontier: list of (cvar, expected_return) tuples
        stocks: {ticker: (cvar, expected_return)}
    """
    if returns.shape[1] < 3:
        return {"frontier": [], "stocks": {}}

    try:
        import cvxpy as cp
    except ImportError:
        _log.warning("cvxpy not installed — efficient frontier unavailable")
        return {"frontier": [], "stocks": {}}

    R = returns.values  # (T, N)
    T, N = R.shape
    alpha = 1 - confidence  # tail probability

    # Individual stock positions
    stocks = {}
    for i, ticker in enumerate(returns.columns):
        stock_returns = R[:, i]
        var = float(-np.percentile(stock_returns, alpha * 100))
        tail = stock_returns[stock_returns <= -var]
        cvar = float(-tail.mean()) if len(tail) > 0 else var
        exp_ret = float(stock_returns.mean() * 252)  # annualised
        stocks[ticker] = (cvar * np.sqrt(252), exp_ret)

    # Sweep risk-aversion levels
    lambdas = np.logspace(-3, 1, n_points)
    frontier = []

    w = cp.Variable(N)
    z = cp.Variable(T)  # auxiliary for CVaR
    gamma = cp.Variable()  # VaR threshold

    portfolio_returns = R @ w
    expected_return = cp.sum(portfolio_returns) / T

    # CVaR constraints: z_t >= -r_t - gamma, z_t >= 0
    constraints = [
        w >= 0,
        cp.sum(w) == 1,
        z >= 0,
        z >= -portfolio_returns - gamma,
    ]
    cvar_expr = gamma + cp.sum(z) / (T * alpha)

    for lam in lambdas:
        objective = cp.Minimize(lam * cvar_expr - expected_return)
        prob = cp.Problem(objective, constraints)
        try:
            prob.solve(solver=cp.CLARABEL, warm_start=True)
            if prob.status in ("optimal", "optimal_inaccurate"):
                cvar_val = float(cvar_expr.value) * np.sqrt(252)  # annualise
                ret_val = float(expected_return.value) * 252
                frontier.append((cvar_val, ret_val))
        except Exception:
            continue

    # Deduplicate and sort by CVaR
    seen = set()
    unique = []
    for cvar_val, ret_val in frontier:
        key = (round(cvar_val, 6), round(ret_val, 6))
        if key not in seen:
            seen.add(key)
            unique.append((cvar_val, ret_val))
    frontier = sorted(unique, key=lambda x: x[0])

    return {"frontier": frontier, "stocks": stocks}


def portfolio_position(
    returns: pd.DataFrame,
    weights: dict[str, float],
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Compute (cvar, expected_return) for a portfolio with given weights.

    Returns annualised values.
    """
    tickers = [t for t in returns.columns if t in weights]
    if not tickers:
        return (0.0, 0.0)

    w = np.array([weights[t] for t in tickers])
    w = w / w.sum()  # normalise

    R = returns[tickers].values
    port_returns = R @ w

    alpha = 1 - confidence
    var = float(-np.percentile(port_returns, alpha * 100))
    tail = port_returns[port_returns <= -var]
    cvar = float(-tail.mean()) if len(tail) > 0 else var

    return (cvar * np.sqrt(252), float(port_returns.mean() * 252))
