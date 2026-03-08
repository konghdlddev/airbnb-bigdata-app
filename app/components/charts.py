import plotly.express as px
import streamlit as st


def neighbourhood_bar_chart(df):
    """Render bar chart for listing counts by neighbourhood."""
    fig = px.bar(
        df,
        x="neighbourhood",
        y="count",
        title="Listings by Neighbourhood",
        color="count",
        color_continuous_scale="Tealgrn",
    )
    fig.update_layout(xaxis_title="Neighbourhood", yaxis_title="Listings")
    st.plotly_chart(fig, use_container_width=True)


def room_type_pie_chart(df):
    """Render pie chart for room-type split."""
    fig = px.pie(df, values="count", names="room_type", title="Room Type Distribution")
    st.plotly_chart(fig, use_container_width=True)


def avg_price_vs_city_center_chart(df):
    """Render average price trend by distance from city center."""
    fig = px.scatter(
        df,
        x="distance_bucket_km",
        y="avg_price",
        size="listing_count",
        title="Average Price vs Distance to City Center",
        labels={
            "distance_bucket_km": "Distance to City Center (km)",
            "avg_price": "Average Price (THB)",
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def average_price_by_zone_chart(df):
    fig = px.bar(
        df,
        x="bangkok_zone",
        y="avg_price",
        color="listing_count",
        title="Average Price by Bangkok Zone",
    )
    st.plotly_chart(fig, use_container_width=True)


def listings_count_by_zone_chart(df):
    fig = px.bar(df, x="bangkok_zone", y="count", title="Listings Count by Bangkok Zone")
    st.plotly_chart(fig, use_container_width=True)


def price_vs_nearest_bts_chart(df):
    fig = px.scatter(
        df,
        x="distance_to_nearest_bts",
        y="price",
        color="bangkok_zone" if "bangkok_zone" in df.columns else None,
        title="Price vs Distance to Nearest BTS",
        opacity=0.5,
    )
    st.plotly_chart(fig, use_container_width=True)


def price_vs_transit_score_chart(df):
    fig = px.scatter(
        df,
        x="transit_accessibility_score",
        y="price",
        color="bangkok_zone" if "bangkok_zone" in df.columns else None,
        title="Price vs Transit Accessibility Score",
        opacity=0.5,
    )
    st.plotly_chart(fig, use_container_width=True)


def tourist_vs_nontourist_chart(df):
    out = df.copy()
    out["area_type"] = out["is_tourist_area"].map({True: "Tourist Area", False: "Non-Tourist Area"})
    fig = px.bar(out, x="area_type", y="avg_price", color="listing_count", title="Tourist vs Non-Tourist Pricing")
    st.plotly_chart(fig, use_container_width=True)


def listings_geo_map(df):
    fig = px.scatter_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        color="price",
        size="price",
        hover_name="name" if "name" in df.columns else None,
        hover_data=[c for c in ["neighbourhood", "bangkok_zone", "price"] if c in df.columns],
        title="Listings Map (Price Colored)",
        zoom=10,
        height=600,
    )
    fig.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(fig, use_container_width=True)
