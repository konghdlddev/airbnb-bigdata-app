import streamlit as st

st.set_page_config(
    page_title="Bangkok Airbnb Big Data App",
    page_icon="🏠",
    layout="wide",
)

st.title("Bangkok Airbnb Big Data Analytics")
st.markdown(
    """
This app combines:
- Spark-based big data analytics
- Natural language listing search
- Price prediction with Spark MLlib
- Geo-aware listing recommendations

Use the left sidebar to open:
- Dashboard
- Natural Language Search
- Price Prediction
- Recommendations
"""
)
