"""Shared UI utilities used across tab modules."""

from __future__ import annotations

import base64
import json
import logging as _logging
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from nicegui import app, ui

_log = _logging.getLogger(__name__)

# Type alias for the shared state dict passed to all tab builders
SharedState = dict[str, Any]

# ── Storage key (matches the Streamlit version's localStorage key) ──
_LS_KEY = "market_dashboard_portfolio"

# ── Encryption for at-rest portfolio data ─────────────────
_STORAGE_SECRET = os.environ.get("STORAGE_SECRET", "market-dashboard-dev-fallback")
if _STORAGE_SECRET == "market-dashboard-dev-fallback":
    _log.warning("Using deterministic fallback encryption secret. Set STORAGE_SECRET env var for production.")
    if os.environ.get("HOST", "127.0.0.1") == "0.0.0.0":
        raise RuntimeError("STORAGE_SECRET must be set in production")
_kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b"market-dashboard-portfolio-salt",
    iterations=480_000,
)
_fernet = Fernet(base64.urlsafe_b64encode(_kdf.derive(_STORAGE_SECRET.encode())))


def get_storage_secret() -> str:
    """Return the storage secret for NiceGUI's storage_secret parameter."""
    return _STORAGE_SECRET


def _get_session_encryption_key() -> bytes | None:
    """Retrieve the per-user encryption key from session storage.

    Stored as base64 string (JSON-safe); decoded to bytes here.
    """
    b64 = app.storage.user.get("encryption_key")
    if not b64:
        return None
    return base64.urlsafe_b64decode(b64.encode())


def _load_local() -> dict:
    """Load portfolio from local browser storage only (no server routing)."""
    raw = app.storage.user.get(_LS_KEY, {})
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
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


def load_portfolio() -> dict:
    """Load and decrypt portfolio — from server if logged in, else local."""
    user_id = app.storage.user.get("user_id")
    encryption_key = _get_session_encryption_key()
    if user_id and encryption_key:
        data = _server_load(encryption_key, user_id)
        # Cache locally for the session
        if data:
            app.storage.user[_LS_KEY] = json.dumps(data, default=str)
        return data

    return _load_local()


def save_portfolio(data: dict) -> None:
    """Encrypt and persist portfolio — to server if logged in, else local."""
    user_id = app.storage.user.get("user_id")
    encryption_key = _get_session_encryption_key()
    if user_id and encryption_key:
        _server_save(data, encryption_key, user_id)
        # Also cache locally
        app.storage.user[_LS_KEY] = json.dumps(data, default=str)
        return

    # Anonymous: local-only
    plaintext = json.dumps(data, default=str).encode()
    app.storage.user[_LS_KEY] = _fernet.encrypt(plaintext).decode()


# ── Server-side portfolio (logged-in users) ───────────────

def _make_user_fernet(encryption_key: bytes) -> Fernet:
    """Build a Fernet cipher from a raw 32-byte per-user key."""
    if len(encryption_key) != 32:
        raise ValueError(f"encryption_key must be 32 bytes, got {len(encryption_key)}")
    return Fernet(base64.urlsafe_b64encode(encryption_key))


def _server_load(encryption_key: bytes, user_id: str) -> dict:
    """Load and decrypt portfolio from the database."""
    from src import db
    row = db.get_portfolio(user_id)
    if not row:
        return {}
    f = _make_user_fernet(encryption_key)
    try:
        decrypted = f.decrypt(
            row["data"] if isinstance(row["data"], bytes) else row["data"].encode()
        )
        parsed = json.loads(decrypted)
        return parsed if isinstance(parsed, dict) else {}
    except (InvalidToken, Exception):
        _log.exception("Failed to decrypt server portfolio for user %s", user_id)
        return {}


def _server_save(data: dict, encryption_key: bytes, user_id: str) -> None:
    """Encrypt and upsert portfolio into the database."""
    from src import db
    f = _make_user_fernet(encryption_key)
    plaintext = json.dumps(data, default=str).encode()
    db.upsert_portfolio(user_id, f.encrypt(plaintext))
