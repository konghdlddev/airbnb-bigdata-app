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

    if parsed.get("landmark_label") and parsed.get("distance_threshold_km") is not None:
        st.subheader("Parsed Landmark")
        st.write(
            f"Detected Landmark: {parsed['landmark_label']} (within {parsed['distance_threshold_km']} km)"
        )

    if parsed.get("zone_code"):
        st.subheader("Parsed Zone")
        st.write(f"Detected Zone: {parsed['zone_code']}")
        st.write("Neighbourhoods used:")
        for neighbourhood in filters.get("neighbourhood_in", []):
            st.write(f"- {neighbourhood}")

    if parsed.get("near_bts_km") is not None or parsed.get("near_mrt_km") is not None:
        st.subheader("Transit Intent")
        if parsed.get("near_bts_km") is not None:
            st.write(f"Near BTS threshold: {parsed['near_bts_km']} km")
        if parsed.get("near_mrt_km") is not None:
            st.write(f"Near MRT threshold: {parsed['near_mrt_km']} km")

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
