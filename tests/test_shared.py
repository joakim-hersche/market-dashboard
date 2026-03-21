"""Tests for encryption round-trip in src.ui.shared."""
import json
import pytest
from src.ui.shared import _fernet


def encrypt_portfolio(data: dict) -> str:
    """Encrypt portfolio data the same way save_portfolio does."""
    plaintext = json.dumps(data, default=str).encode()
    return _fernet.encrypt(plaintext).decode()


def decrypt_portfolio(raw) -> dict:
    """Decrypt portfolio data the same way load_portfolio does."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        from cryptography.fernet import InvalidToken
        try:
            decrypted = _fernet.decrypt(raw.encode())
            parsed = json.loads(decrypted)
            return parsed if isinstance(parsed, dict) else {}
        except InvalidToken:
            pass
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def test_encrypt_decrypt_round_trip():
    original = {
        "portfolio": {
            "AAPL": [{"shares": 10, "buy_price": 150.0, "purchase_date": "2024-01-15"}],
        },
        "currency": "USD",
    }
    encrypted = encrypt_portfolio(original)
    assert isinstance(encrypted, str)
    assert encrypted != json.dumps(original)

    decrypted = decrypt_portfolio(encrypted)
    assert decrypted == original


def test_unencrypted_dict_passes_through():
    raw = {"portfolio": {"MSFT": [{"shares": 5, "buy_price": 300.0, "purchase_date": "2024-06-01"}]}}
    result = decrypt_portfolio(raw)
    assert result == raw


def test_unencrypted_json_string_passes_through():
    raw_dict = {"portfolio": {"TSLA": [{"shares": 2, "buy_price": 200.0, "purchase_date": "2024-03-01"}]}}
    raw_str = json.dumps(raw_dict)
    result = decrypt_portfolio(raw_str)
    assert result == raw_dict


def test_empty_portfolio_round_trip():
    original = {}
    encrypted = encrypt_portfolio(original)
    decrypted = decrypt_portfolio(encrypted)
    assert decrypted == original


def test_load_portfolio_from_server(monkeypatch, tmp_path):
    """When user_id is in storage, load from DB instead of local."""
    import os
    os.environ.pop("DATABASE_URL", None)
    monkeypatch.setenv("MASTER_KEY", "ab" * 32)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))

    from src import db, auth
    db._init_connection(str(tmp_path / "test.db"))
    db.init_schema()

    user_id, _ = auth.register("sync@example.com", "password123")
    db.mark_email_verified(user_id)
    result = auth.login("sync@example.com", "password123")

    # Save portfolio to server
    from src.ui.shared import _server_save, _server_load
    test_data = {"portfolio": {"AAPL": [{"shares": 5}]}, "currency": "CHF"}
    _server_save(test_data, result["encryption_key"], user_id)

    # Load it back
    loaded = _server_load(result["encryption_key"], user_id)
    assert loaded["portfolio"]["AAPL"][0]["shares"] == 5
    assert loaded["currency"] == "CHF"

    db._close_connection()


def test_server_load_returns_empty_when_no_portfolio(monkeypatch, tmp_path):
    import os
    os.environ.pop("DATABASE_URL", None)
    monkeypatch.setenv("MASTER_KEY", "ab" * 32)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))

    from src import db, auth
    db._init_connection(str(tmp_path / "test.db"))
    db.init_schema()

    user_id, _ = auth.register("empty@example.com", "password123")
    db.mark_email_verified(user_id)
    result = auth.login("empty@example.com", "password123")

    from src.ui.shared import _server_load
    loaded = _server_load(result["encryption_key"], user_id)
    assert loaded == {}

    db._close_connection()
