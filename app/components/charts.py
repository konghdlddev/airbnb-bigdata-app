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
