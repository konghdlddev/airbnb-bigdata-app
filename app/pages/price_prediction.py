import streamlit as st

from app.services.prediction_service import get_area_options, predict_listing_price

st.title("ทำนายราคา")
st.caption("ประเมินราคาที่พักจากคุณลักษณะของประกาศ")

area_options = get_area_options()
default_area = "Ratchathewi" if "Ratchathewi" in area_options else area_options[0]

with st.form("price_prediction_form"):
    st.subheader("ส่วนที่ 1: รายละเอียดที่พัก")
    room_type = st.selectbox(
        "ประเภทห้อง",
        ["Entire home/apt", "Private room", "Shared room"],
        index=0,
    )
    st.caption("ประเภทที่พักที่เปิดให้จอง")

    neighbourhood = st.selectbox("พื้นที่", options=area_options, index=area_options.index(default_area))
    st.caption("เขตที่ตั้งของที่พัก")

    minimum_nights = st.number_input(
        "จำนวนคืนขั้นต่ำ", min_value=1, max_value=365, value=2
    )
    st.caption("จำนวนคืนขั้นต่ำที่ผู้เข้าพักต้องจอง")

    st.subheader("ส่วนที่ 2: ความนิยม")
    number_of_reviews = st.number_input(
        "จำนวนรีวิวทั้งหมด", min_value=0, max_value=10000, value=20
    )
    st.caption("จำนวนรีวิวทั้งหมดของประกาศนี้")

    st.subheader("ส่วนที่ 3: ความพร้อมให้จอง")
    availability_365 = st.slider(
        "จำนวนวันที่เปิดจองต่อปี", min_value=0, max_value=365, value=180, step=1
    )
    st.caption("จำนวนวันที่เปิดให้จองได้ภายใน 1 ปี")

    submit = st.form_submit_button("ทำนายราคา")

if submit:
    payload = {
        "room_type": room_type,
        "neighbourhood": neighbourhood,
        "minimum_nights": minimum_nights,
        "number_of_reviews": number_of_reviews,
        "availability_365": availability_365,
    }
    try:
        predicted_price = predict_listing_price(payload)
        st.subheader("ราคาที่คาดการณ์ต่อคืน")
        st.success(f"ราคาที่คาดการณ์: {predicted_price:,.0f} บาท/คืน")
        st.info("การประเมินนี้อิงจากทำเล ประเภทห้อง ความนิยม และความพร้อมให้จอง")
    except RuntimeError as e:
        st.error(str(e))

st.markdown("---")
st.markdown(
    """
**ตัวอย่างข้อมูล**

ที่พักทั้งหลังในเขตราชเทวี  
พักขั้นต่ำ: 2 คืน  
รีวิว: 20  
วันเปิดจอง: 180
"""
)
