import os
import sys
from pathlib import Path

# Fix Streamlit + PyTorch conflict: file watcher tries to inspect torch.classes and raises
# "Tried to instantiate class '__path__._path', but it does not exist" - disable watcher
os.environ.setdefault("STREAMLIT_SERVER_ENABLE_FILE_WATCHER", "false")

# Patch PyTorch ก่อนโหลด Streamlit — หลีกเลี่ยง torch.classes error ที่ทำให้ Natural Language Search ล้มเหลว
try:
    import torch
    if hasattr(torch, "classes") and hasattr(torch.classes, "__path__"):
        torch.classes.__path__ = []
except Exception:
    pass

# Ensure project root is in path so app.* imports work when pages are loaded by st.navigation
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="ระบบวิเคราะห์ Airbnb กรุงเทพ",
    page_icon="🏠",
    layout="wide",
)


def _home_page():
    st.title("ระบบวิเคราะห์ข้อมูล Airbnb กรุงเทพ")
    st.markdown(
        """
แอปนี้ประกอบด้วย:
- การวิเคราะห์ข้อมูลขนาดใหญ่ด้วย Spark
- การค้นหาที่พักด้วยภาษาธรรมชาติ
- การทำนายราคาด้วย Spark MLlib
- ระบบแนะนำที่พักแบบอ้างอิงภูมิศาสตร์

เลือกเมนูจากแถบด้านซ้าย:
- แดชบอร์ด
- Natural Language Search
- ทำนายราคา
- แนะนำที่พัก
"""
    )


# กำหนดเมนูในแถบด้านซ้าย: แก้ title และ icon ได้ตามต้องการ
# ใช้ views/ แทน pages/ เพื่อหลีกเลี่ยง conflict กับ Streamlit (มี pages/ ทำให้ stcore/health 404)
pages = [
    st.Page(_home_page, title="หน้าหลัก", icon="🏠", default=True),
    st.Page("views/dashboard.py", title="แดชบอร์ด", icon="📊"),
    st.Page("views/natural_language_search.py", title="Natural Language Search", icon="🔍"),
    st.Page("views/price_prediction.py", title="ทำนายราคา", icon="💰"),
    st.Page("views/recommendations.py", title="แนะนำที่พัก", icon="📍"),
]

pg = st.navigation(pages)
pg.run()
