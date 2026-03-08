import streamlit as st

from app.components.charts import neighbourhood_bar_chart, room_type_pie_chart
from app.components.metrics import show_main_metrics
from app.services.analytics_service import get_kpis, listings_by_neighbourhood, room_type_distribution

st.title("Dashboard")
st.caption("Overview of listings, prices, and distribution patterns.")

kpis = get_kpis()
show_main_metrics(kpis["total_listings"], kpis["average_price"])

neigh_df = listings_by_neighbourhood()
room_df = room_type_distribution()

col1, col2 = st.columns(2)
with col1:
    neighbourhood_bar_chart(neigh_df)
with col2:
    room_type_pie_chart(room_df)
