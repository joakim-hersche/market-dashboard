"""Tests for DataProvider protocol and YFinanceProvider."""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.providers import DataProvider, YFinanceProvider


def test_yfinance_provider_satisfies_protocol():
    """YFinanceProvider must implement all DataProvider methods."""
    provider = YFinanceProvider()
    assert isinstance(provider, DataProvider)


@patch("src.providers.yf.download")
def test_get_current_prices_returns_dict(mock_download):
    close_data = pd.DataFrame({"Close": [150.0, 151.0]})
    mock_download.return_value = close_data
    provider = YFinanceProvider()
    result = provider.get_current_prices(["AAPL"])
    assert isinstance(result, dict)
    assert "AAPL" in result


@patch("src.providers.yf.Ticker")
def test_get_company_name_returns_string(mock_ticker):
    mock_ticker.return_value.info = {"shortName": "Apple Inc."}
    provider = YFinanceProvider()
    assert provider.get_company_name("AAPL") == "Apple Inc."


@patch("src.providers.yf.Ticker")
def test_get_company_name_fallback_to_ticker(mock_ticker):
    mock_ticker.return_value.info = {}
    provider = YFinanceProvider()
    assert provider.get_company_name("AAPL") == "AAPL"
