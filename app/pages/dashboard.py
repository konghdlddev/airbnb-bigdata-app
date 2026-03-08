import streamlit as st

from app.components.charts import (
    avg_price_vs_city_center_chart,
    average_price_by_zone_chart,
    listings_count_by_zone_chart,
    listings_geo_map,
    neighbourhood_bar_chart,
    price_vs_nearest_bts_chart,
    price_vs_transit_score_chart,
    room_type_pie_chart,
    tourist_vs_nontourist_chart,
)
from app.components.metrics import show_main_metrics
from app.services.analytics_service import (
    average_price_vs_distance_to_city_center,
    average_price_by_bangkok_zone,
    geo_map_points,
    get_kpis,
    listings_count_by_zone,
    listings_by_neighbourhood,
    price_vs_nearest_bts,
    price_vs_transit_accessibility,
    room_type_distribution,
    tourist_area_price_comparison,
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

zone_avg_df = average_price_by_bangkok_zone()
zone_count_df = listings_count_by_zone()

if zone_avg_df is not None and not zone_avg_df.empty:
    average_price_by_zone_chart(zone_avg_df)

if zone_count_df is not None and not zone_count_df.empty:
    listings_count_by_zone_chart(zone_count_df)

bts_df = price_vs_nearest_bts()
if bts_df is not None and not bts_df.empty:
    price_vs_nearest_bts_chart(bts_df)

transit_df = price_vs_transit_accessibility()
if transit_df is not None and not transit_df.empty:
    price_vs_transit_score_chart(transit_df)

tourist_df = tourist_area_price_comparison()
if tourist_df is not None and not tourist_df.empty:
    tourist_vs_nontourist_chart(tourist_df)

map_df = geo_map_points()
if map_df is not None and not map_df.empty:
    listings_geo_map(map_df)
