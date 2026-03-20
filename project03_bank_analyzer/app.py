"""
Project 03 — Streamlit UI for the Bank Statement Financial Analyzer.

Run:  streamlit run app.py
"""
import os
import sys
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from graph import graph  # noqa: E402

st.set_page_config(page_title="Bank Statement Financial Analyzer", layout="wide")
st.title("🏦 Personal Bank Statement Financial Analyzer")
st.markdown(
    "Upload up to **3 months** of bank statements (CSV). "
    "The pipeline categorizes transactions, detects anomalies, benchmarks vs 50/30/20, "
    "and writes a personalized financial health report."
)

with st.sidebar:
    st.header("Upload CSV Statement(s)")
    uploaded_files = st.file_uploader(
        "Bank Statement CSV(s)", type=["csv"], accept_multiple_files=True
    )
    st.markdown(
        "**Expected columns:** `date`, `description`, `amount`  \n"
        "Column names are auto-detected from common bank export formats."
    )
    run_button = st.button(
        "📊 Analyze Finances", type="primary", disabled=(not uploaded_files)
    )

if run_button and uploaded_files:
    # Combine multiple CSV files into one temp file
    dfs = []
    for f in uploaded_files[:3]:
        try:
            dfs.append(pd.read_csv(f))
        except Exception as exc:
            st.error(f"Could not read {f.name}: {exc}")

    if not dfs:
        st.error("No valid CSV files uploaded.")
        st.stop()

    combined = pd.concat(dfs, ignore_index=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        combined.to_csv(tmp, index=False)
        tmp_path = tmp.name

    with st.spinner("Running multi-agent financial analysis… (this may take 60–90 seconds)"):
        try:
            result = graph.invoke({"raw_csv_path": tmp_path})
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
            st.stop()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    st.success("Analysis complete!")

    # --- Report ---
    st.subheader("📝 Financial Health Report")
    st.markdown(result.get("report", "No report generated."))

    # --- Budget Breakdown ---
    budget = result.get("budget_analysis", {})
    if budget:
        col1, col2, col3 = st.columns(3)
        col1.metric("Needs", f"{budget.get('needs_pct', 0):.1f}%", budget.get("needs_status", ""))
        col2.metric("Wants", f"{budget.get('wants_pct', 0):.1f}%", budget.get("wants_status", ""))
        col3.metric("Savings", f"{budget.get('savings_pct', 0):.1f}%", budget.get("savings_status", ""))
        st.info(budget.get("overall_verdict", ""))

    # --- Spending chart ---
    categorized = result.get("categorized", [])
    if categorized:
        df_cat = pd.DataFrame(categorized)
        spending_df = df_cat[df_cat["category"] != "income"]
        if not spending_df.empty:
            cat_totals = spending_df.groupby("category")["amount"].sum().reset_index()
            fig = px.pie(
                cat_totals, names="category", values="amount",
                title="Spending by Category", hole=0.4,
            )
            st.plotly_chart(fig, use_container_width=True)

        # Monthly trend
        df_cat["date"] = pd.to_datetime(df_cat["date"], errors="coerce")
        df_cat["month"] = df_cat["date"].dt.to_period("M").astype(str)
        monthly = spending_df.copy()
        monthly["date"] = pd.to_datetime(monthly["date"], errors="coerce")
        monthly["month"] = monthly["date"].dt.to_period("M").astype(str)
        monthly_totals = monthly.groupby(["month", "category"])["amount"].sum().reset_index()
        if not monthly_totals.empty:
            fig2 = px.bar(
                monthly_totals, x="month", y="amount", color="category",
                title="Monthly Spending by Category",
            )
            st.plotly_chart(fig2, use_container_width=True)

    # --- Anomalies ---
    anomalies = result.get("anomalies", {})
    stat_anomalies = anomalies.get("statistical", [])
    pattern_anomalies = anomalies.get("pattern", [])
    total_anomalies = len(stat_anomalies) + len(pattern_anomalies)

    if total_anomalies > 0:
        st.subheader(f"⚠️ Anomalies Detected ({total_anomalies})")
        if stat_anomalies:
            with st.expander(f"📈 Statistical Anomalies ({len(stat_anomalies)})"):
                st.dataframe(pd.DataFrame(stat_anomalies))
        if pattern_anomalies:
            with st.expander(f"🔍 Pattern Anomalies ({len(pattern_anomalies)})"):
                st.dataframe(pd.DataFrame(pattern_anomalies))
    else:
        st.success("✅ No anomalies detected.")
