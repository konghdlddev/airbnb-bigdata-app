import streamlit as st

from app.services.recommendation_service import (
    get_listing_details,
    get_listing_id_options,
    recommend_similar_listings,
)

st.title("แนะนำที่พัก")
st.caption("ค้นหาที่พักใกล้เคียงจากโซน ประเภทห้อง การเดินทาง ความเป็นย่านท่องเที่ยว และรูปแบบราคา")

listing_ids = get_listing_id_options()
if not listing_ids:
    st.warning("ไม่พบรหัสประกาศในชุดข้อมูล Gold กรุณารัน ETL ก่อน")
    st.stop()

with st.form("recommendations_form"):
    listing_id = st.selectbox("รหัสประกาศต้นทาง", options=listing_ids, index=0)
    top_k = st.slider("Top K", min_value=3, max_value=20, value=10, step=1)
    submitted = st.form_submit_button("แนะนำที่พัก")

if submitted:
    details = get_listing_details(int(listing_id))
    if details:
        st.subheader("ข้อมูลประกาศต้นทาง")
        st.json(
            {
                "id": details.get("id"),
                "name": details.get("name"),
                "neighbourhood": details.get("neighbourhood"),
                "bangkok_zone": details.get("bangkok_zone"),
                "room_type": details.get("room_type"),
                "price": details.get("price"),
                "distance_to_nearest_bts": details.get("distance_to_nearest_bts"),
                "distance_to_nearest_mrt": details.get("distance_to_nearest_mrt"),
                "transit_accessibility_score": details.get("transit_accessibility_score"),
                "is_tourist_area": details.get("is_tourist_area"),
            }
        )

    recommendations = recommend_similar_listings(int(listing_id), limit=int(top_k))
    if recommendations is None or recommendations.empty:
        st.warning("ยังไม่พบรายการแนะนำสำหรับประกาศนี้")
    else:
        st.subheader("รายการแนะนำ")
        st.dataframe(recommendations, use_container_width=True)
