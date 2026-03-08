import json

import streamlit as st

from app.components.tables import show_dataframe
from app.services.search_service import get_processed_preview, run_natural_language_search

st.title("ค้นหาภาษาธรรมชาติ")
st.caption("พิมพ์คำค้น เช่น 'ห้องแถวบางนา ราคาไม่เกิน 1200' หรือ 'ห้องส่วนตัว ใกล้ bts'.")

show_dataframe(get_processed_preview(limit=5), "ตัวอย่างข้อมูลที่ประมวลผลแล้ว (5 แถวแรก)")

query = st.text_input("คำค้นหา", placeholder="ห้องทั้งหลัง ย่านราชเทวี")

if query:
    parsed, filters, filter_logic, result_df = run_natural_language_search(query, limit=10)

    if parsed.get("landmark_label") and parsed.get("distance_threshold_km") is not None:
        st.subheader("ผลตีความแลนด์มาร์ก")
        st.write(
            f"พบแลนด์มาร์ก: {parsed['landmark_label']} (ในระยะ {parsed['distance_threshold_km']} กม.)"
        )

    if parsed.get("zone_code"):
        st.subheader("ผลตีความโซน")
        st.write(f"โซนที่ตรวจพบ: {parsed['zone_code']}")
        st.write("เขตที่ใช้ในการค้นหา:")
        for neighbourhood in filters.get("neighbourhood_in", []):
            st.write(f"- {neighbourhood}")

    if parsed.get("near_bts_km") is not None or parsed.get("near_mrt_km") is not None:
        st.subheader("เงื่อนไขการเดินทาง")
        if parsed.get("near_bts_km") is not None:
            st.write(f"ใกล้ BTS ไม่เกิน: {parsed['near_bts_km']} กม.")
        if parsed.get("near_mrt_km") is not None:
            st.write(f"ใกล้ MRT ไม่เกิน: {parsed['near_mrt_km']} กม.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("คำค้นที่ระบบตีความ")
        st.code(json.dumps(parsed, indent=2), language="json")
    with col2:
        st.subheader("ฟิลเตอร์ที่นำไปใช้")
        st.code(json.dumps(filters, indent=2), language="json")

    st.subheader("ตรรกะการกรอง")
    st.code(filter_logic)

    show_dataframe(result_df, "รายการที่ตรงเงื่อนไข")
