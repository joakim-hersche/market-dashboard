import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from src.stocks import get_sp500_stocks

# --- Page Config ---
st.set_page_config(page_title="Market Dashboard", layout="wide")
st.title("Market Dashboard")
st.markdown("Build and track your stock portfolio in real time.")

# --- Session State ---
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}

# --- Stock List ---
stock_options = get_sp500_stocks()

# --- Portfolio Input ---
col1, col2 = st.columns(2)

with col1:
    selected = st.selectbox(
        "Select a Stock",
        options=list(stock_options.keys()),
        index=None,
        placeholder="e.g. Apple Inc. (AAPL)"
    )
with col2:
    shares = st.number_input("Number of Shares", min_value=0.0, value=None, step=1.0, placeholder="e.g. 5")

# Add on button click OR when Enter is pressed in shares field
add = st.button("Add to Portfolio")

if add:
    if selected is None or shares is None or shares == 0:
        st.warning("Please select a stock and enter a number of shares.")
    else:
        ticker = stock_options[selected]
        st.session_state.portfolio[ticker] = shares
        st.success(f"Added {shares} shares of {ticker}")

# --- Display Portfolio ---
if st.session_state.portfolio:
    st.subheader("Portfolio Overview")

    rows = []
    for t, s in st.session_state.portfolio.items():
        data = yf.Ticker(t).history(period="5d")
        
        if len(data) < 2:
            continue
            
        current_price = data["Close"].iloc[-1]
        prev_price = data["Close"].iloc[-2]
        daily_pnl = (current_price - prev_price) * s
        total_value = current_price * s

        rows.append({
            "Ticker": t,
            "Shares": s,
            "Current Price": round(current_price, 2),
            "Total Value": round(total_value, 2),
            "Daily P&L": round(daily_pnl, 2)
        })

    df = pd.DataFrame(rows)

    # --- Summary Metrics ---
    total_portfolio_value = df["Total Value"].sum()
    total_daily_pnl = df["Daily P&L"].sum()

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric("Total Portfolio Value", f"${total_portfolio_value:,.2f}")
    metric2.metric("Daily P&L", f"${total_daily_pnl:,.2f}")
    metric3.metric("Number of Positions", len(df))

    st.dataframe(df.set_index("Ticker"), use_container_width=True)

    # --- Price History Charts ---
    st.subheader("Price History")

    for t in st.session_state.portfolio:
        hist = yf.Ticker(t).history(period="6mo")
        hist.index = hist.index.tz_localize(None)

        fig = px.line(hist, x=hist.index, y="Close", title=f"{t} — 6 Month Price History")
        fig.update_layout(xaxis_title="Date", yaxis_title="Price (USD)")
        st.plotly_chart(fig, use_container_width=True)

    # --- Normalised Comparison Chart ---
    st.subheader("Normalised Performance Comparison")

    comparison_data = {}
    for t in st.session_state.portfolio:
        hist = yf.Ticker(t).history(period="6mo")
        hist.index = hist.index.tz_localize(None)
        comparison_data[t] = hist["Close"]

    comparison_df = pd.DataFrame(comparison_data)
    comparison_df = comparison_df / comparison_df.iloc[0] * 100

    fig = px.line(comparison_df, x=comparison_df.index, y=comparison_df.columns,
                  title="Normalised Performance (Base 100)")
    fig.update_layout(xaxis_title="Date", yaxis_title="Normalised Price (Base 100)")
    fig.add_hline(y=100, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)