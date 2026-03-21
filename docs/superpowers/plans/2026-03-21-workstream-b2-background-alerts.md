# Workstream B2 — Background Alert Emails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a daily background job at 07:00 CET that checks portfolio alert rules for opted-in users and emails them a digest of new warnings.

**Architecture:** A new `src/alert_job.py` module runs an asyncio sleep-loop scheduled for 07:00 CET daily. For each opted-in user, it decrypts their portfolio, computes weights via `build_portfolio_df`, runs `evaluate_all()` from `src/alerts.py`, diffs against last-sent alert IDs, and sends a digest email via Resend if anything is new. The `users` table gets two new columns (`email_alerts`, `last_alert_ids`). The top bar gets an account dropdown with an email alert toggle, and a one-time opt-in prompt shows on first verified login.

**Tech Stack:** Python 3.12, NiceGUI 3.8, asyncio, zoneinfo, Resend, pytest

**Spec:** `docs/superpowers/specs/2026-03-21-workstream-b2-background-alerts-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/db.py` | Modify | Add email_alerts/last_alert_ids columns, migration, new query functions |
| `src/alert_job.py` | Create | Scheduler loop, per-user check, email builder |
| `main.py` | Modify | Start scheduler, account dropdown, opt-in prompt |
| `tests/test_db.py` | Modify | Tests for new columns and queries |
| `tests/test_alert_job.py` | Create | Scheduler logic, diff logic, email construction |

---

## Task 1: Database Schema Migration + New Queries

**Files:**
- Modify: `src/db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Write failing tests for new columns and queries**

Append to `tests/test_db.py`:

```python
# ── Email alert preference queries ──


def test_email_alerts_default_is_none():
    """New users have email_alerts = None (never asked)."""
    user_id = db.create_user("alerts@example.com", "hash", b"key")
    user = db.get_user_by_id(user_id)
    assert user["email_alerts"] is None


def test_set_and_get_email_alerts():
    user_id = db.create_user("toggle@example.com", "hash", b"key")
    db.set_email_alerts(user_id, True)
    assert db.get_email_alerts(user_id) is True
    db.set_email_alerts(user_id, False)
    assert db.get_email_alerts(user_id) is False


def test_get_alerted_users():
    """Only verified users with email_alerts=True are returned."""
    u1 = db.create_user("on@example.com", "hash", b"key")
    db.mark_email_verified(u1)
    db.set_email_alerts(u1, True)

    u2 = db.create_user("off@example.com", "hash", b"key")
    db.mark_email_verified(u2)
    db.set_email_alerts(u2, False)

    u3 = db.create_user("unverified@example.com", "hash", b"key")
    db.set_email_alerts(u3, True)  # verified=False, should be excluded

    u4 = db.create_user("null@example.com", "hash", b"key")
    db.mark_email_verified(u4)
    # email_alerts is None — should be excluded

    users = db.get_alerted_users()
    ids = [u["id"] for u in users]
    assert u1 in ids
    assert u2 not in ids
    assert u3 not in ids
    assert u4 not in ids


def test_update_last_alert_ids():
    user_id = db.create_user("last@example.com", "hash", b"key")
    db.update_last_alert_ids(user_id, ["concentration_AAPL", "correlation_MSFT_GOOGL"])
    user = db.get_user_by_id(user_id)
    import json
    assert json.loads(user["last_alert_ids"]) == ["concentration_AAPL", "correlation_MSFT_GOOGL"]


def test_last_alert_ids_default_empty():
    user_id = db.create_user("empty_alerts@example.com", "hash", b"key")
    user = db.get_user_by_id(user_id)
    import json
    assert json.loads(user["last_alert_ids"]) == []
```

- [ ] **Step 2: Run tests — confirm they fail**

Run: `pytest tests/test_db.py -v -k "email_alerts or last_alert"`
Expected: failures — columns and functions don't exist yet

- [ ] **Step 3: Add migration and new functions to `src/db.py`**

Add to `init_schema()`, after the existing `CREATE TABLE` statements (inside both the postgres and sqlite branches), add `ALTER TABLE` calls:

```python
    # ── Migrations (safe to re-run) ───────────────────────
    # B2: email alert preferences
    try:
        _execute("ALTER TABLE users ADD COLUMN email_alerts %s DEFAULT NULL" %
                 ("BOOLEAN" if _backend == "postgres" else "INTEGER"))
    except Exception:
        pass  # Column already exists
    try:
        _execute("ALTER TABLE users ADD COLUMN last_alert_ids TEXT DEFAULT '[]'")
    except Exception:
        pass  # Column already exists
```

Add new query functions after the existing user queries section:

```python
# ── Email alert queries ───────────────────────────────


def get_email_alerts(user_id: str) -> bool | None:
    """Return the user's email_alerts preference (True/False/None)."""
    ph = _p(1)[0]
    row = _fetchone(f"SELECT email_alerts FROM users WHERE id = {ph}", (user_id,))
    if not row:
        return None
    val = row["email_alerts"]
    if val is None:
        return None
    if _backend == "sqlite":
        return bool(val)
    return val


def set_email_alerts(user_id: str, enabled: bool) -> None:
    """Set the user's email alert preference."""
    ph = _p(2)
    val = enabled if _backend == "postgres" else int(enabled)
    _execute(
        f"UPDATE users SET email_alerts = {ph[0]} WHERE id = {ph[1]}",
        (val, user_id),
    )


def get_alerted_users() -> list[dict]:
    """Return all verified users who have opted in to email alerts."""
    if _backend == "postgres":
        return _fetchall(
            "SELECT * FROM users WHERE email_verified = TRUE AND email_alerts = TRUE"
        )
    return _fetchall(
        "SELECT * FROM users WHERE email_verified = 1 AND email_alerts = 1"
    )


def update_last_alert_ids(user_id: str, rule_ids: list[str]) -> None:
    """Persist the rule_id list from the last alert email sent."""
    import json
    ph = _p(2)
    _execute(
        f"UPDATE users SET last_alert_ids = {ph[0]} WHERE id = {ph[1]}",
        (json.dumps(rule_ids), user_id),
    )
```

- [ ] **Step 4: Run tests — confirm they pass**

Run: `pytest tests/test_db.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: add email_alerts and last_alert_ids columns with queries"
```

---

## Task 2: Alert Job Core Logic (`src/alert_job.py`)

**Files:**
- Create: `src/alert_job.py`
- Create: `tests/test_alert_job.py`

- [ ] **Step 1: Write failing tests for the alert job**

```python
# tests/test_alert_job.py
"""Tests for src.alert_job — per-user check logic and email construction."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock

os.environ.pop("DATABASE_URL", None)

from src import db, auth
from src.alert_job import check_user_alerts, build_alert_email, compute_new_alerts


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SQLITE_PATH", db_path)
    monkeypatch.setenv("MASTER_KEY", "ab" * 32)
    db._init_connection(db_path)
    db.init_schema()
    auth._rate_limits.clear()
    yield
    db._close_connection()


def _create_opted_in_user(email="test@example.com"):
    """Helper: register, verify, opt in, return (user_id, encryption_key)."""
    user_id, _ = auth.register(email, "password123")
    db.mark_email_verified(user_id)
    db.set_email_alerts(user_id, True)
    result = auth.login(email, "password123")
    return user_id, result["encryption_key"]


# ── compute_new_alerts ──


def test_compute_new_alerts_all_new():
    current = ["concentration_AAPL", "correlation_MSFT_GOOGL"]
    last_sent = []
    new = compute_new_alerts(current, last_sent)
    assert set(new) == {"concentration_AAPL", "correlation_MSFT_GOOGL"}


def test_compute_new_alerts_some_new():
    current = ["concentration_AAPL", "correlation_MSFT_GOOGL"]
    last_sent = ["concentration_AAPL"]
    new = compute_new_alerts(current, last_sent)
    assert new == ["correlation_MSFT_GOOGL"]


def test_compute_new_alerts_none_new():
    current = ["concentration_AAPL"]
    last_sent = ["concentration_AAPL", "correlation_MSFT_GOOGL"]
    new = compute_new_alerts(current, last_sent)
    assert new == []


# ── build_alert_email ──


def test_build_alert_email_single():
    from src.alerts import Alert
    alerts = [Alert("critical", "Concentration risk", "AAPL is 47%", "concentration_AAPL")]
    subject, html = build_alert_email(alerts)
    assert "AAPL" in subject
    assert "47%" in html
    assert "critical" in html.lower() or "EF4444" in html


def test_build_alert_email_multiple():
    from src.alerts import Alert
    alerts = [
        Alert("critical", "Concentration risk", "AAPL is 47%", "concentration_AAPL"),
        Alert("warning", "High correlation", "MSFT and GOOGL 91%", "correlation_MSFT_GOOGL"),
    ]
    subject, html = build_alert_email(alerts)
    assert "2" in subject
    assert "AAPL" in html
    assert "MSFT" in html


# ── check_user_alerts (integration) ──


@patch("src.alert_job.build_portfolio_df")
@patch("src.alert_job._send_alert_email")
def test_check_user_alerts_sends_on_new(mock_send, mock_build_df):
    """When new alerts are detected, email is sent and last_alert_ids updated."""
    import pandas as pd
    user_id, enc_key = _create_opted_in_user()

    # Save a portfolio with a concentrated position
    from src.ui.shared import _server_save
    portfolio_data = {"portfolio": {"AAPL": [{"shares": 100, "buy_price": 150.0, "purchase_date": "2024-01-01"}]}}
    _server_save(portfolio_data, enc_key, user_id)

    # Mock build_portfolio_df to return a df with high concentration
    mock_df = pd.DataFrame({
        "Ticker": ["AAPL"],
        "Total Value": [15000.0],
    })
    mock_build_df.return_value = mock_df

    check_user_alerts(user_id, enc_key)

    mock_send.assert_called_once()
    # Verify last_alert_ids was updated
    user = db.get_user_by_id(user_id)
    stored_ids = json.loads(user["last_alert_ids"])
    assert "concentration_AAPL" in stored_ids


@patch("src.alert_job.build_portfolio_df")
@patch("src.alert_job._send_alert_email")
def test_check_user_alerts_skips_when_no_new(mock_send, mock_build_df):
    """When all alerts were already sent, no email is sent."""
    import pandas as pd
    user_id, enc_key = _create_opted_in_user("skip@example.com")

    from src.ui.shared import _server_save
    portfolio_data = {"portfolio": {"AAPL": [{"shares": 100, "buy_price": 150.0, "purchase_date": "2024-01-01"}]}}
    _server_save(portfolio_data, enc_key, user_id)

    # Pre-set last_alert_ids so nothing is "new"
    db.update_last_alert_ids(user_id, ["concentration_AAPL"])

    mock_df = pd.DataFrame({"Ticker": ["AAPL"], "Total Value": [15000.0]})
    mock_build_df.return_value = mock_df

    check_user_alerts(user_id, enc_key)

    mock_send.assert_not_called()


@patch("src.alert_job.build_portfolio_df")
@patch("src.alert_job._send_alert_email")
def test_check_user_alerts_skips_empty_portfolio(mock_send, mock_build_df):
    """Users with empty portfolios get no email."""
    user_id, enc_key = _create_opted_in_user("empty@example.com")

    from src.ui.shared import _server_save
    _server_save({"portfolio": {}}, enc_key, user_id)

    import pandas as pd
    mock_build_df.return_value = pd.DataFrame()

    check_user_alerts(user_id, enc_key)

    mock_send.assert_not_called()
```

- [ ] **Step 2: Run tests — confirm they fail**

Run: `pytest tests/test_alert_job.py -v`
Expected: `ModuleNotFoundError: No module named 'src.alert_job'`

- [ ] **Step 3: Implement `src/alert_job.py`**

```python
# src/alert_job.py
"""Background alert job — daily portfolio checks with email digest.

Runs as an asyncio task inside the NiceGUI process.
Checks opted-in users at 07:00 CET daily.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
from zoneinfo import ZoneInfo

from src import db
from src.alerts import evaluate_all
from src.auth import _unwrap_key
from src.portfolio import build_portfolio_df
from src.ui.shared import _server_load

_log = logging.getLogger(__name__)

CET = ZoneInfo("Europe/Zurich")
SCHEDULE_HOUR = 7
SCHEDULE_MINUTE = 0


# ── Scheduler ─────────────────────────────────────────────


def start_alert_scheduler() -> None:
    """Launch the daily alert check as a background asyncio task."""
    asyncio.create_task(_run_daily_loop())
    _log.info("Alert scheduler started — next run at %02d:%02d CET", SCHEDULE_HOUR, SCHEDULE_MINUTE)


async def _run_daily_loop() -> None:
    """Sleep until 07:00 CET, run checks, repeat."""
    while True:
        now = datetime.datetime.now(CET)
        target = now.replace(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        sleep_seconds = (target - now).total_seconds()
        _log.info("Alert job sleeping %.0f seconds until %s", sleep_seconds, target.isoformat())
        await asyncio.sleep(sleep_seconds)

        try:
            await _run_all_checks()
        except Exception:
            _log.exception("Alert job failed")


async def _run_all_checks() -> None:
    """Process all opted-in users."""
    from nicegui import run

    users = await run.io_bound(db.get_alerted_users)
    _log.info("Alert job running for %d users", len(users))

    for user in users:
        try:
            enc_key = user["encryption_key"]
            if not isinstance(enc_key, bytes):
                enc_key = enc_key.encode()
            raw_key = _unwrap_key(enc_key)
            await run.io_bound(check_user_alerts, user["id"], raw_key)
        except Exception:
            _log.exception("Alert check failed for user %s", user["id"])


# ── Per-user check ────────────────────────────────────────


def check_user_alerts(user_id: str, encryption_key: bytes) -> None:
    """Check alerts for a single user. Send email if new alerts found."""
    # Load portfolio
    portfolio_data = _server_load(encryption_key, user_id)
    portfolio = portfolio_data.get("portfolio", {})
    if not portfolio:
        return

    currency = portfolio_data.get("currency", "USD")
    settings = portfolio_data.get("_alerts", {}).get("settings", {})

    # Compute weights
    df = build_portfolio_df(portfolio, currency)
    if df.empty:
        return

    total_value = df["Total Value"].sum()
    if total_value <= 0:
        return

    weights = {}
    for ticker in portfolio:
        ticker_value = df[df["Ticker"] == ticker]["Total Value"].sum()
        weights[ticker] = ticker_value / total_value

    # Evaluate concentration alerts only. Correlation alerts are skipped in the
    # background job because they require 1y price history per ticker pair —
    # fetching that for every user daily is too expensive. Users still see
    # correlation alerts when they open the Overview tab (warm cache only).
    alerts = evaluate_all(weights, price_data=None, settings=settings)
    if not alerts:
        return

    # Diff against last-sent
    current_ids = [a.rule_id for a in alerts]
    user = db.get_user_by_id(user_id)
    last_sent = json.loads(user.get("last_alert_ids", "[]"))

    new_ids = compute_new_alerts(current_ids, last_sent)
    if not new_ids:
        return

    # Filter to only new alerts for the email
    new_alerts = [a for a in alerts if a.rule_id in new_ids]

    # Send email
    email = user["email"]
    subject, html = build_alert_email(new_alerts)
    _send_alert_email(email, subject, html)

    # Update last-sent state
    db.update_last_alert_ids(user_id, current_ids)


def compute_new_alerts(current_ids: list[str], last_sent_ids: list[str]) -> list[str]:
    """Return rule_ids that are in current but not in last_sent."""
    last_set = set(last_sent_ids)
    return [rid for rid in current_ids if rid not in last_set]


# ── Email construction ────────────────────────────────────


_SEVERITY_COLORS = {
    "critical": "#EF4444",
    "warning": "#F59E0B",
    "info": "#3B82F6",
}


def build_alert_email(alerts: list) -> tuple[str, str]:
    """Build subject line and HTML body for an alert digest email.

    Returns (subject, html_body).
    """
    if len(alerts) == 1:
        subject = f"Portfolio Alert: {alerts[0].message}"
    else:
        subject = f"Portfolio Alert: {len(alerts)} new warnings"

    app_url = os.environ.get("APP_URL", "http://localhost:8080")

    cards = []
    for a in alerts:
        color = _SEVERITY_COLORS.get(a.severity, "#3B82F6")
        cards.append(
            f'<div style="border-left:4px solid {color}; padding:8px 12px; margin:8px 0;'
            f' background:rgba(0,0,0,0.05); border-radius:4px;">'
            f'<strong style="color:{color}; text-transform:uppercase; font-size:12px;">'
            f'{a.severity} — {a.title}</strong><br>'
            f'<span style="font-size:14px;">{a.message}</span></div>'
        )

    html = (
        f'<div style="font-family:sans-serif; max-width:500px; margin:0 auto;">'
        f'<h2 style="font-size:18px; margin-bottom:4px;">Market Dashboard — Portfolio Alerts</h2>'
        f'<p style="color:#666; font-size:14px;">'
        f'{len(alerts)} new alert{"s" if len(alerts) != 1 else ""} detected for your portfolio:</p>'
        f'{"".join(cards)}'
        f'<hr style="border:none; border-top:1px solid #ddd; margin:16px 0;">'
        f'<p style="font-size:12px; color:#888;">'
        f'<a href="{app_url}" style="color:#3B82F6;">Manage alert settings in your dashboard</a><br>'
        f'You\'re receiving this because you enabled email alerts.</p>'
        f'</div>'
    )

    return subject, html


# ── Email sending ─────────────────────────────────────────


def _send_alert_email(to_email: str, subject: str, html: str) -> None:
    """Send an alert digest email via Resend."""
    api_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("FROM_EMAIL", "noreply@example.com")
    if not api_key:
        _log.warning("RESEND_API_KEY not set — skipping alert email to %s", to_email)
        return
    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "html": html,
        })
    except Exception:
        _log.exception("Failed to send alert email to %s", to_email)
```

- [ ] **Step 4: Run tests — confirm they pass**

Run: `pytest tests/test_alert_job.py -v`
Expected: all tests PASS

- [ ] **Step 5: Run full suite**

Run: `pytest -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/alert_job.py tests/test_alert_job.py
git commit -m "feat: add background alert job with per-user checks and email digest"
```

---

## Task 3: Main App Integration (Scheduler + Account Dropdown + Opt-in Prompt)

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add scheduler start to `_preload()`**

Add import at the top of `main.py` (after the existing `from src import db` line):

```python
from src.alert_job import start_alert_scheduler
```

Add to end of `_preload()`:

```python
    start_alert_scheduler()
```

- [ ] **Step 2: Replace auth button block with account dropdown**

Replace the existing auth button block (lines ~465-512, from `# ── Auth button` through the Sign in button's closing `)`) with:

```python
            # ── Auth / account ────────────────────────────
            auth_user_id = app.storage.user.get("user_id")
            auth_email = app.storage.user.get("auth_email")

            if auth_user_id:
                with ui.button(auth_email or "", icon="expand_more").props(
                    "flat dense no-caps size=sm color=none"
                ).style(
                    f"border:1px solid {BORDER_INPUT}; border-radius:6px; padding:0 10px;"
                    f" height:28px; color:{TEXT_MUTED} !important; font-size:11px;"
                    f" max-width:180px; overflow:hidden; text-overflow:ellipsis;"
                ):
                    with ui.menu().style(
                        f"background:{BG_CARD}; border:1px solid rgba(255,255,255,0.12);"
                        f" border-radius:10px; min-width:220px;"
                    ):
                        # Email alerts toggle
                        with ui.menu_item().style("padding:10px 14px;"):
                            with ui.row().classes("items-center gap-3 no-wrap w-full"):
                                ui.label("Email alerts").style(
                                    f"font-size:13px; color:{TEXT_PRIMARY}; font-weight:500;"
                                )
                                alert_pref = app.storage.user.get("_email_alerts_cached")
                                alert_switch = ui.switch(value=bool(alert_pref)).props("dense")

                                async def _toggle_alerts(e):
                                    await run.io_bound(db.set_email_alerts, auth_user_id, e.value)
                                    app.storage.user["_email_alerts_cached"] = e.value

                                alert_switch.on_value_change(_toggle_alerts)

                        ui.separator().style("margin:4px 14px; opacity:0.15;")

                        # Sign out
                        def _logout():
                            app.storage.user.pop("user_id", None)
                            app.storage.user.pop("encryption_key", None)
                            app.storage.user.pop("auth_email", None)
                            app.storage.user.pop("_email_alerts_cached", None)
                            ui.navigate.to("/")

                        with ui.menu_item(on_click=_logout).style("padding:10px 14px;"):
                            ui.label("Sign out").style(
                                f"font-size:13px; color:{TEXT_PRIMARY};"
                            )
            else:
                async def _show_sign_in():
                    async def _on_login_success(result):
                        import base64 as _b64
                        app.storage.user["user_id"] = result["user_id"]
                        app.storage.user["encryption_key"] = _b64.urlsafe_b64encode(
                            result["encryption_key"]
                        ).decode()
                        app.storage.user["auth_email"] = result["email"]
                        await _maybe_migrate_local_portfolio(result)
                        ui.navigate.to("/")

                    for name in _TAB_NAMES:
                        _tab_built[name] = False
                    _content_container.clear()
                    with _content_container:
                        await show_auth_ui(_content_container, _on_login_success)

                ui.button("Sign in", on_click=_show_sign_in).props(
                    "flat dense no-caps size=sm color=none"
                ).style(
                    f"border:1px solid {BORDER_INPUT}; border-radius:6px; padding:0 10px;"
                    f" height:28px; color:{TEXT_MUTED} !important; font-size:11px;"
                )
```

- [ ] **Step 3: Add opt-in prompt after portfolio load**

After the unverified-user banner block (around line ~316), add:

```python
    # Show email alert opt-in prompt (one-time, for verified users never asked)
    if user_id:
        email_alerts_pref = await run.io_bound(db.get_email_alerts, user_id)
        # Cache for the account dropdown toggle
        app.storage.user["_email_alerts_cached"] = email_alerts_pref

        if email_alerts_pref is None and user_row and user_row["email_verified"]:
            with ui.dialog() as optin_dlg, ui.card().style(
                f"min-width:360px; max-width:440px; background:{BG_CARD};"
                f" border:1px solid rgba(255,255,255,0.12); border-radius:10px; padding:24px;"
            ):
                ui.label("Stay on top of your portfolio").style(
                    f"font-size:16px; font-weight:700; color:{TEXT_PRIMARY}; margin-bottom:8px;"
                )
                ui.label(
                    "We can email you when we detect concentration risk or high "
                    "correlation in your holdings. One email per day, only when "
                    "something changes."
                ).style(f"font-size:13px; color:{TEXT_MUTED}; margin-bottom:20px; line-height:1.5;")
                with ui.row().classes("w-full justify-end gap-2"):
                    async def _opt_out():
                        await run.io_bound(db.set_email_alerts, user_id, False)
                        app.storage.user["_email_alerts_cached"] = False
                        optin_dlg.close()

                    async def _opt_in():
                        await run.io_bound(db.set_email_alerts, user_id, True)
                        app.storage.user["_email_alerts_cached"] = True
                        optin_dlg.close()

                    ui.button("No thanks", on_click=_opt_out).props(
                        "flat no-caps"
                    ).style(f"color:{TEXT_MUTED}; font-size:13px;")
                    ui.button("Enable alerts", on_click=_opt_in).props(
                        "no-caps unelevated"
                    ).style(f"background:{ACCENT}; border-radius:8px; font-size:13px;")
            optin_dlg.open()
```

- [ ] **Step 4: Verify syntax**

Run: `python3 -c "import ast; ast.parse(open('main.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`
Expected: all tests PASS

- [ ] **Step 6: Test manually**

Run: `python3 main.py`
1. Log in with a verified account — opt-in prompt should appear
2. Click "Enable alerts" — dialog closes
3. Click the account dropdown (email button) — toggle shows ON
4. Toggle OFF and back ON — verify it persists across page reload
5. Check terminal logs — scheduler should show "Alert scheduler started"

- [ ] **Step 7: Commit**

```bash
git add main.py
git commit -m "feat: account dropdown, email alert opt-in prompt, scheduler startup"
```

---

## Task 4: Full Test Suite Pass

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`
Expected: all tests PASS. Fix any failures.

- [ ] **Step 2: Commit if any fixes needed**

```bash
git add -u
git commit -m "fix: address test failures from B2 integration"
```
