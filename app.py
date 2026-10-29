from pathlib import Path
import json

import streamlit as st

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
REFRESH_SECONDS = 2

st.set_page_config(page_title="Thai License Plate OCR", page_icon="🚗", layout="centered")

st.markdown(
    """
    <style>
    .plate-box {
        background: #fff;
        color: #111;
        border: 4px solid #222;
        border-radius: 14px;
        text-align: center;
        font-size: 3rem;
        font-weight: 800;
        padding: 4px 10px;
        margin: 4px 0 10px 0;
        letter-spacing: 2px;
    }
    .sub { color: #888; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Thai License Plate OCR")
st.caption("กดปุ่มเพื่อถ่ายรูป ระบบจะอ่านป้ายและตรวจสอบสิทธิ์ให้อัตโนมัติ")


def latest_image():
    files = [p for p in IMAGES_DIR.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def load_report(path: Path):
    report = path.with_suffix(".json")
    if not report.exists():
        return None
    try:
        return json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"allowed": False, "message": f"อ่านผลไม่ได้: {e}", "result": None}


def show_result(path: Path, report: dict):
    st.image(str(path), caption=path.name, width="stretch")

    if report["allowed"]:
        st.success("อนุญาตให้ผ่าน")
    else:
        st.error(f"ไม่อนุญาตให้ผ่าน — {report['message']}")

    result = report.get("result")
    if not result or not result.get("success"):
        if result:
            with st.expander("ดู API Response"):
                st.json(result)
        return

    data = result.get("data", {}) or {}
    plates = data.get("plates", []) or []

    if not plates:
        st.warning("ไม่พบทะเบียนรถในรูปนี้")
        return

    for i, plate in enumerate(plates, start=1):
        if len(plates) > 1:
            st.subheader(f"รถคันที่ {i}")
        st.markdown(
            f"<div class='plate-box'>{plate.get('plate_number') or '-'}</div>",
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("สีป้าย", plate.get("plate_color") or "-")
        c2.metric("ประเภท", plate.get("plate_type") or "-")
        c3.metric("Normalized", plate.get("plate_number_normalized") or "-")

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("จังหวัด/พื้นที่", data.get("region_text") or "-")
    c2.metric("ประเทศ", data.get("country_guess") or "-")
    conf = data.get("confidence_score")
    c3.metric("ความมั่นใจ", f"{conf:.0%}" if isinstance(conf, (int, float)) and conf <= 1 else (conf or "-"))

    with st.expander("ดู API Response ทั้งหมด"):
        st.json(result)


@st.fragment(run_every=REFRESH_SECONDS)
def watcher():
    path = latest_image()

    if path is None:
        st.info("ยังไม่มีรูป — กดปุ่มเพื่อถ่ายรูป")
        return

    report = load_report(path)
    if report is None:
        st.image(str(path), caption=path.name, width="stretch")
        st.info("กำลังอ่านป้ายทะเบียน...")
        return

    show_result(path, report)


watcher()