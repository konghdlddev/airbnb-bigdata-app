import streamlit as st


def show_main_metrics(total_listings: int, average_price: float):
    """Render KPI cards for high-level summary metrics."""
    col1, col2 = st.columns(2)
    col1.metric("Total Listings", f"{total_listings:,}")
    col2.metric("Average Price (THB)", f"{average_price:,.2f}")
