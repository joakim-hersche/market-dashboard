"""Paywall UI — locked tab overlay and pricing page."""
from __future__ import annotations

from nicegui import app, run, ui

from src.billing import (
    get_display_prices, create_checkout_session, is_pro,
    _LOCKED_TAB_DESCRIPTIONS,
)
from src.theme import (
    ACCENT, BG_CARD, BG_MAIN, BORDER_SUBTLE,
    TEXT_DIM, TEXT_MUTED, TEXT_PRIMARY,
)


def render_locked_overlay(tab_name: str, currency: str) -> None:
    """Render a locked tab overlay with upgrade CTA."""
    description = _LOCKED_TAB_DESCRIPTIONS.get(tab_name, "This feature requires Pro")
    prices = get_display_prices(currency)
    symbol = prices["symbol"]
    monthly = prices["monthly"]

    with ui.column().classes("w-full items-center justify-center").style(
        "min-height:400px; padding:40px 20px;"
    ):
        # Blurred placeholder
        ui.html(
            '<div style="width:100%; max-width:600px; height:200px; border-radius:12px;'
            ' background:linear-gradient(135deg, rgba(59,130,246,0.08), rgba(139,92,246,0.08));'
            ' filter:blur(2px); margin-bottom:32px;"></div>'
        )

        ui.icon("lock").style("font-size:32px; color:rgba(255,255,255,0.3); margin-bottom:12px;")
        ui.label("Upgrade to Pro").style(
            f"font-size:22px; font-weight:700; color:{TEXT_PRIMARY}; margin-bottom:8px;"
        )
        ui.label(description).style(
            f"font-size:14px; color:{TEXT_MUTED}; margin-bottom:20px; text-align:center; max-width:400px;"
        )
        ui.label(f"From {symbol}{monthly}/month").style(
            f"font-size:13px; color:{TEXT_DIM}; margin-bottom:16px;"
        )
        ui.button("View plans", on_click=lambda: ui.navigate.to("/pricing")).props(
            "no-caps unelevated"
        ).style(f"background:{ACCENT}; border-radius:8px; font-size:14px; padding:8px 24px;")


def build_pricing_page(user_id: str | None, currency: str) -> None:
    """Build the /pricing page content."""
    prices = get_display_prices(currency)
    symbol = prices["symbol"]
    user_is_pro = is_pro(user_id)
    email = app.storage.user.get("auth_email")

    with ui.column().classes("w-full items-center").style(
        f"background:{BG_MAIN}; min-height:100vh; padding:40px 20px;"
    ):
        ui.label("Market Dashboard Pro").style(
            f"font-size:28px; font-weight:700; color:{TEXT_PRIMARY}; margin-bottom:8px;"
        )
        ui.label("Unlock the full power of your portfolio tracker").style(
            f"font-size:14px; color:{TEXT_MUTED}; margin-bottom:32px;"
        )

        # Interval selector
        selected_interval = {"value": "yearly"}

        interval_row = ui.row().classes("items-center gap-2").style("margin-bottom:32px;")

        def _update_interval(interval: str):
            selected_interval["value"] = interval
            _refresh_cards()

        with interval_row:
            for iv in ["monthly", "yearly", "lifetime"]:
                ui.button(
                    iv.capitalize(),
                    on_click=lambda i=iv: _update_interval(i),
                ).props("flat no-caps").style(
                    f"border:1px solid {BORDER_SUBTLE}; border-radius:6px; padding:4px 16px;"
                    f" font-size:13px; color:{TEXT_MUTED};"
                )

        # Cards container
        @ui.refreshable
        def _refresh_cards():
            iv = selected_interval["value"]
            price = prices[iv]
            period = {"monthly": "/month", "yearly": "/year", "lifetime": " one-time"}[iv]

            with ui.row().classes("items-start gap-6 justify-center flex-wrap"):
                # Free card
                with ui.card().style(
                    f"width:280px; background:{BG_CARD}; border:1px solid rgba(255,255,255,0.08);"
                    f" border-radius:12px; padding:28px;"
                ):
                    ui.label("Free").style(f"font-size:20px; font-weight:700; color:{TEXT_PRIMARY}; margin-bottom:4px;")
                    ui.label(f"{symbol}0").style(f"font-size:28px; font-weight:700; color:{TEXT_PRIMARY}; margin-bottom:16px;")
                    _feature_list([
                        ("Up to 10 positions", True),
                        ("Overview & Positions", True),
                        ("Portfolio Health", True),
                        ("Research & Guide", True),
                        ("Monte Carlo Forecast", False),
                        ("Income tracking", False),
                        ("Excel export", False),
                        ("Email alerts", False),
                    ])

                # Pro card
                with ui.card().style(
                    f"width:280px; background:{BG_CARD}; border:2px solid {ACCENT};"
                    f" border-radius:12px; padding:28px;"
                ):
                    ui.label("Pro").style(f"font-size:20px; font-weight:700; color:{ACCENT}; margin-bottom:4px;")
                    ui.label(f"{symbol}{price}{period}").style(
                        f"font-size:28px; font-weight:700; color:{TEXT_PRIMARY}; margin-bottom:16px;"
                    )
                    _feature_list([
                        ("Unlimited positions", True),
                        ("Overview & Positions", True),
                        ("Portfolio Health", True),
                        ("Research & Guide", True),
                        ("Monte Carlo Forecast", True),
                        ("Income tracking", True),
                        ("Excel export", True),
                        ("Email alerts", True),
                    ])
                    ui.html('<div style="height:12px;"></div>')

                    if user_is_pro:
                        ui.label("You're on Pro").style(
                            f"font-size:13px; color:{ACCENT}; font-weight:600; text-align:center; width:100%;"
                        )
                    elif not user_id:
                        ui.button("Sign in to upgrade", on_click=lambda: ui.navigate.to("/")).props(
                            "no-caps unelevated"
                        ).style(f"width:100%; background:{ACCENT}; border-radius:8px;")
                    else:
                        async def _checkout(interval=iv):
                            url = await run.io_bound(
                                create_checkout_session, user_id, email, currency, interval
                            )
                            ui.navigate.to(url, new_tab=False)

                        ui.button("Get started", on_click=_checkout).props(
                            "no-caps unelevated"
                        ).style(f"width:100%; background:{ACCENT}; border-radius:8px;")

        _refresh_cards()


def _feature_list(features: list[tuple[str, bool]]) -> None:
    """Render a feature checklist."""
    for label, included in features:
        icon = "check_circle" if included else "cancel"
        color = "#22C55E" if included else "rgba(255,255,255,0.2)"
        with ui.row().classes("items-center gap-2").style("margin-bottom:6px;"):
            ui.icon(icon).style(f"font-size:16px; color:{color};")
            ui.label(label).style(f"font-size:13px; color:{TEXT_MUTED};")
