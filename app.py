# app.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="برآوردگر قیمت خانه در بروجرد", layout="centered")
st.title("🏠 برآوردگر قیمت خانه در بروجرد — با درصد آپشن‌ها و دقت تخمین")

# -----------------------------
# لیست محله‌ها و قیمت پایه (تومان / متر مربع)
# -----------------------------
NEIGHBORHOODS = {
    "بهار": 20_000_000,
    "جهاد": 18_500_000,
    "گلدشت": 18_000_000,
    "ولیعصر": 17_500_000,
    "رستمی": 17_000_000,
    "مخابرات": 16_500_000,
    "اندیشه": 15_500_000,
    "بهشت": 15_000_000,
    "شهرک دانشگاه": 14_500_000,
    "انقلاب": 14_000_000,
    "شاهد": 13_500_000,
    "جمهوری": 13_000_000,
    "شهداء": 12_500_000,
}

# -----------------------------
# درصد آپشن‌ها وابسته به محله
# -----------------------------
OPTION_PCTS = {
    "بهار": {"room_pct": 0.06, "yard_pct": 0.10, "villa_pct": 0.13, "elevator_pct": 0.06, "heating_pct": 0.04, "parking_pct": 0.10},
    "جهاد": {"room_pct": 0.055, "yard_pct": 0.09, "villa_pct": 0.125, "elevator_pct": 0.055, "heating_pct": 0.035, "parking_pct": 0.09},
    "گلدشت": {"room_pct": 0.05, "yard_pct": 0.085, "villa_pct": 0.12, "elevator_pct": 0.05, "heating_pct": 0.03, "parking_pct": 0.08},
    "ولیعصر": {"room_pct": 0.048, "yard_pct": 0.08, "villa_pct": 0.115, "elevator_pct": 0.048, "heating_pct": 0.028, "parking_pct": 0.075},
    "رستمی": {"room_pct": 0.045, "yard_pct": 0.078, "villa_pct": 0.11, "elevator_pct": 0.045, "heating_pct": 0.027, "parking_pct": 0.07},
    "مخابرات": {"room_pct": 0.043, "yard_pct": 0.075, "villa_pct": 0.108, "elevator_pct": 0.043, "heating_pct": 0.025, "parking_pct": 0.065},
    "اندیشه": {"room_pct": 0.04, "yard_pct": 0.07, "villa_pct": 0.10, "elevator_pct": 0.04, "heating_pct": 0.022, "parking_pct": 0.06},
    "بهشت": {"room_pct": 0.038, "yard_pct": 0.065, "villa_pct": 0.095, "elevator_pct": 0.038, "heating_pct": 0.02, "parking_pct": 0.055},
    "شهرک دانشگاه": {"room_pct": 0.035, "yard_pct": 0.06, "villa_pct": 0.09, "elevator_pct": 0.035, "heating_pct": 0.018, "parking_pct": 0.05},
    "انقلاب": {"room_pct": 0.033, "yard_pct": 0.058, "villa_pct": 0.088, "elevator_pct": 0.033, "heating_pct": 0.017, "parking_pct": 0.048},
    "شاهد": {"room_pct": 0.03, "yard_pct": 0.055, "villa_pct": 0.085, "elevator_pct": 0.03, "heating_pct": 0.015, "parking_pct": 0.045},
    "جمهوری": {"room_pct": 0.028, "yard_pct": 0.05, "villa_pct": 0.08, "elevator_pct": 0.028, "heating_pct": 0.013, "parking_pct": 0.04},
    "شهداء": {"room_pct": 0.025, "yard_pct": 0.045, "villa_pct": 0.075, "elevator_pct": 0.025, "heating_pct": 0.012, "parking_pct": 0.035},
}

# فرضیه انحراف معیار تقریبی برای محله‌ها (برای محاسبه درصد اطمینان)
NEIGHBORHOOD_STD = {
    "بهار": 2_500_000, "جهاد": 2_000_000, "گلدشت": 1_800_000, "ولیعصر": 1_700_000,
    "رستمی": 1_600_000, "مخابرات": 1_500_000, "اندیشه": 1_400_000, "بهشت": 1_300_000,
    "شهرک دانشگاه": 1_200_000, "انقلاب": 1_100_000, "شاهد": 1_000_000, "جمهوری": 950_000, "شهداء": 900_000
}

def fmt_toman(x):
    try:
        x = int(round(x))
        return f"{x:,} تومان"
    except:
        return str(x)

def nice_round(x):
    return int(round(x / 1000.0)) * 1000

# -----------------------------
# ورودی کاربر
# -----------------------------
st.header("مشخصات ملک")

neighborhood = st.selectbox("📍 محله", list(NEIGHBORHOODS.keys()))
size = st.number_input("📐 متراژ (متر مربع)", min_value=30, max_value=2000, value=100)
rooms = st.slider("🛏️ تعداد اتاق", 1, 10, 2)
yard = st.selectbox("🌳 حیاط دارد؟", ["خیر", "بله"])
building_type = st.selectbox("🏢 نوع بنا", ["آپارتمان", "ویلا"])
elevator = st.selectbox("🛗 آسانسور دارد؟", ["خیر", "بله"])
heating = st.selectbox("🔥 سیستم گرمایش دارد؟", ["خیر", "بله"])
parking = st.selectbox("🅿️ پارکینگ دارد؟", ["خیر", "بله"])

if st.button("📊 محاسبه قیمت"):
    base_price = NEIGHBORHOODS[neighborhood]
    std = NEIGHBORHOOD_STD.get(neighborhood, 1_000_000)
    adjust_pct = 0.0
    adjust_detail = {}

    # اتاق‌ها
    room_pct = max(0, rooms - 1) * OPTION_PCTS[neighborhood]["room_pct"]
    adjust_pct += room_pct
    adjust_detail["اتاق‌ها"] = room_pct

    # سایر امکانات
    if yard == "بله":
        adjust_pct += OPTION_PCTS[neighborhood]["yard_pct"]
        adjust_detail["حیاط"] = OPTION_PCTS[neighborhood]["yard_pct"]
    if building_type == "ویلا":
        adjust_pct += OPTION_PCTS[neighborhood]["villa_pct"]
        adjust_detail["ویلا"] = OPTION_PCTS[neighborhood]["villa_pct"]
    if elevator == "بله":
        adjust_pct += OPTION_PCTS[neighborhood]["elevator_pct"]
        adjust_detail["آسانسور"] = OPTION_PCTS[neighborhood]["elevator_pct"]
    if heating == "بله":
        adjust_pct += OPTION_PCTS[neighborhood]["heating_pct"]
        adjust_detail["گرمایش"] = OPTION_PCTS[neighborhood]["heating_pct"]
    if parking == "بله":
        adjust_pct += OPTION_PCTS[neighborhood]["parking_pct"]
        adjust_detail["پارکینگ"] = OPTION_PCTS[neighborhood]["parking_pct"]

    # محاسبه قیمت
    adj_price_per_m2 = base_price * (1 + adjust_pct)
    total_price = adj_price_per_m2 * size
    adj_price_per_m2_n = nice_round(adj_price_per_m2)
    total_price_n = nice_round(total_price)

    # -----------------------------
    # درصد اطمینان
    # -----------------------------
    confidence = max(0, min(100, 100 * (1 - (std / base_price))))  # درصد دقت تخمین

    # -----------------------------
    # خروجی
    # -----------------------------
    st.subheader("نتیجه تخمینی")
    st.write(f"💰 **قیمت پایه هر متر در محله {neighborhood}:** {fmt_toman(base_price)}")
    st.write(f"📐 **قیمت هر متر پس از تعدیل:** {fmt_toman(adj_price_per_m2_n)}")
    st.success(f"🏡 **قیمت کل (برای {size} متر): {fmt_toman(total_price_n)}**")
    st.markdown("📊 **درصد افزوده شده از آپشن‌ها:**")
    for k, v in adjust_detail.items():
        st.write(f"- {k}: {v*100:.1f}%")
    st.write(f"💹 **درصد کل تعدیل:** {adjust_pct*100:.1f}%")
    st.write(f"🔎 **درصد دقت تخمین:** {confidence:.1f}%")

    st.info("توجه: این برآورد تقریبی است و بر اساس داده‌های تجربی و ضرایب وابسته به محله محاسبه شده. برای دقت بیشتر، داده‌های به‌روز از آگهی‌های واقعی جمع‌آوری شود.")
