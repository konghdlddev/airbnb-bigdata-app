import streamlit as st

from app.services.prediction_service import get_area_options, predict_listing_price

st.title("Price Prediction")
st.caption("Estimate listing price based on listing attributes.")

area_options = get_area_options()
default_area = "Ratchathewi" if "Ratchathewi" in area_options else area_options[0]

with st.form("price_prediction_form"):
    st.subheader("Section 1: Listing Details")
    room_type = st.selectbox(
        "Room Type",
        ["Entire home/apt", "Private room", "Shared room"],
        index=0,
    )
    st.caption("The type of accommodation offered.")

    neighbourhood = st.selectbox("Area", options=area_options, index=area_options.index(default_area))
    st.caption("The neighbourhood where the listing is located.")

    minimum_nights = st.number_input(
        "Minimum Stay (Nights)", min_value=1, max_value=365, value=2
    )
    st.caption("Minimum number of nights guests must book.")

    st.subheader("Section 2: Popularity")
    number_of_reviews = st.number_input(
        "Total Reviews", min_value=0, max_value=10000, value=20
    )
    st.caption("Total number of guest reviews for the listing.")

    st.subheader("Section 3: Availability")
    availability_365 = st.slider(
        "Available Days per Year", min_value=0, max_value=365, value=180, step=1
    )
    st.caption("How many days the listing is available for booking in a year.")

    submit = st.form_submit_button("Predict Price")

if submit:
    payload = {
        "room_type": room_type,
        "neighbourhood": neighbourhood,
        "minimum_nights": minimum_nights,
        "number_of_reviews": number_of_reviews,
        "availability_365": availability_365,
    }
    predicted_price = predict_listing_price(payload)

    st.subheader("Predicted Price per Night")
    st.success(f"Predicted Price: {predicted_price:,.0f} THB per night")
    st.info("This estimate is based on location, room type, popularity, and availability.")

st.markdown("---")
st.markdown(
    """
**Example Scenario**

Entire home in Ratchathewi  
Minimum stay: 2 nights  
Reviews: 20  
Available days: 180
"""
)
