import streamlit as st

from app.services.recommendation_service import (
    get_listing_details,
    get_listing_id_options,
    get_price_bounds,
    get_zone_options,
    recommend_by_zone_and_price,
    recommend_similar_listings,
)

st.title("แนะนำที่พัก")
st.caption("ค้นหาที่พักใกล้เคียงจากโซน ประเภทห้อง การเดินทาง ความเป็นย่านท่องเที่ยว และรูปแบบราคา")

listing_ids = get_listing_id_options()
zone_options = get_zone_options()
if not listing_ids and not zone_options:
    st.warning("ไม่พบข้อมูลประกาศในชุดข้อมูล Gold กรุณารัน ETL ก่อน")
    st.stop()

tab1, tab2 = st.tabs(["เลือกตามโซนและราคา", "เลือกจากประกาศต้นทาง"])

with tab1:
    st.subheader("แนะนำตามโซนและงบประมาณ")
    price_bounds = get_price_bounds()
    default_min = int(price_bounds["min_price"]) if price_bounds["min_price"] > 0 else 300
    default_max = int(min(price_bounds["max_price"], 5000)) if price_bounds["max_price"] > 0 else 5000

    with st.form("recommendations_zone_price_form"):
        selected_zone = st.selectbox("โซน", options=zone_options, index=0 if zone_options else None)
        min_price = st.number_input("ราคาต่ำสุด (บาท/คืน)", min_value=0, value=default_min, step=100)
        max_price = st.number_input("ราคาสูงสุด (บาท/คืน)", min_value=0, value=max(default_max, default_min), step=100)
        top_k_zone = st.slider("Top K", min_value=3, max_value=30, value=10, step=1, key="topk_zone")
        submitted_zone = st.form_submit_button("ค้นหาที่พักตามโซนและราคา")

    if submitted_zone:
        results = recommend_by_zone_and_price(
            zone_code=str(selected_zone),
            min_price=float(min_price),
            max_price=float(max_price),
            limit=int(top_k_zone),
        )
        if results is None or results.empty:
            st.warning("ไม่พบรายการที่ตรงโซนและช่วงราคาที่เลือก")
        else:
            st.success(f"พบ {len(results)} รายการในโซน {selected_zone}")
            st.dataframe(results, use_container_width=True)

with tab2:
    if not listing_ids:
        st.info("ไม่พบรายการสำหรับโหมดนี้")
    else:
        with st.form("recommendations_form"):
            listing_id = st.selectbox("รหัสประกาศต้นทาง", options=listing_ids, index=0)
            top_k = st.slider("Top K", min_value=3, max_value=20, value=10, step=1, key="topk_listing")
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
