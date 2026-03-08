import streamlit as st

from app.components.charts import (
    avg_price_vs_city_center_chart,
    neighbourhood_bar_chart,
    room_type_pie_chart,
)
from app.components.metrics import show_main_metrics
from app.services.analytics_service import (
    average_price_vs_distance_to_city_center,
    get_kpis,
    listings_by_neighbourhood,
    room_type_distribution,
)

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

distance_price_df = average_price_vs_distance_to_city_center(bucket_km=1.0)
if distance_price_df is not None and not distance_price_df.empty:
    avg_price_vs_city_center_chart(distance_price_df)
