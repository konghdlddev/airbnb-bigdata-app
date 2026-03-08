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
