import json

import streamlit as st

from app.components.tables import show_dataframe
from app.services.search_service import get_processed_preview, run_natural_language_search

st.title("Natural Language Search")
st.caption("Type a query like: 'cheap room in Bang Na' or 'private room under 1500'.")

show_dataframe(get_processed_preview(limit=5), "Processed Dataset Preview (First 5 Rows)")

query = st.text_input("Search query", placeholder="entire home in Ratchathewi")

if query:
    parsed, filters, filter_logic, result_df = run_natural_language_search(query, limit=10)

    if parsed.get("zone_code"):
        st.subheader("Parsed Zone")
        zone_name = parsed.get("zone_name") or parsed["zone_code"]
        st.write(f"Detected Zone: {zone_name}")
        st.write("Neighbourhoods used:")
        for neighbourhood in parsed.get("zone_neighbourhoods", []):
            st.write(f"- {neighbourhood}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Parsed Query")
        st.code(json.dumps(parsed, indent=2), language="json")
    with col2:
        st.subheader("Applied Filters")
        st.code(json.dumps(filters, indent=2), language="json")

    st.subheader("Filter Logic")
    st.code(filter_logic)

    show_dataframe(result_df, "Matching Listings")
