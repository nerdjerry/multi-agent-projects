"""
Project 04 — Streamlit UI for the AI Stock Research & Investment Brief Generator.

Run:  streamlit run app.py
"""
import os
import sys

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from graph import graph  # noqa: E402

st.set_page_config(page_title="AI Stock Research Brief", layout="wide")
st.title("📈 AI Stock Research & Investment Brief Generator")
st.markdown(
    "Enter a stock ticker. Three research agents run in **parallel** (fundamentals, news sentiment, "
    "technicals), then an AI brief writer synthesizes an opinionated one-page investment brief."
)

with st.sidebar:
    st.header("Stock Lookup")
    ticker_input = st.text_input(
        "Ticker Symbol",
        placeholder="e.g. MSFT, AAPL, RELIANCE.NS",
        help="Use .NS for NSE India, .BO for BSE India",
    ).strip().upper()
    run_button = st.button("🔍 Generate Brief", type="primary", disabled=(not ticker_input))
    st.markdown("---")
    st.markdown("**Examples:** MSFT · GOOGL · TSLA · RELIANCE.NS · INFY.NS")

if run_button and ticker_input:
    with st.spinner(f"Running 3 parallel research agents for **{ticker_input}**… (30–60 seconds)"):
        try:
            result = graph.invoke({"ticker": ticker_input})
        except Exception as exc:
            st.error(f"Pipeline failed: {exc}")
            st.stop()

    st.success(f"Research complete for **{ticker_input}**!")

    # --- Investment Brief (hero section) ---
    st.subheader("📋 Investment Brief")
    brief = result.get("investment_brief", "No brief generated.")
    st.markdown(brief)

    st.divider()

    # --- Three specialist reports ---
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🏦 Fundamentals")
        st.markdown(result.get("fundamentals_report", "No report."))

    with col2:
        st.subheader("📰 News Sentiment")
        st.markdown(result.get("sentiment_report", "No report."))

    with col3:
        st.subheader("📊 Technical Analysis")
        st.markdown(result.get("technical_report", "No report."))
