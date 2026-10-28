# train_model.py
import pandas as pd
import json
import os

# فایل ورودی: manual_house_data.csv (تولید شده توسط scrape)
INPUT_CSV = "manual_house_data.csv"  # یا "house_prices.csv" اگر با اسم دیگری ذخیره شده
OUT_DIR = "models"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_STATS = os.path.join(OUT_DIR, "neighborhood_stats.json")

print("🔍 Loading data from:", INPUT_CSV)
df = pd.read_csv(INPUT_CSV)

# انتظار داریم ستون price (ریال) و size (متر) وجود داشته باشد
# حذف ردیف‌های ناقص
df = df.dropna(subset=["price","size"]).copy()

# اگر قیمت به صورت رشته است: پاکسازی
def clean_to_int(x):
    try:
        if isinstance(x, str):
            x = "".join(ch for ch in x if ch.isdigit())
            return int(x) if x else None
        return int(x)
    except:
        return None

df["price"] = df["price"].apply(clean_to_int)
df["size"] = df["size"].apply(clean_to_int)
df = df.dropna(subset=["price","size"]).copy()

# تبدیل ریال -> تومان (قیمت‌ها در CSV ممکن است ریال یا تومان باشند؛ فرض می‌کنیم ریال)
# اگر داده‌های CSV شما قبلاً تومان هستند، در اینجا 10 تقسیم نکنید.
# برای اطمینان: اگر مقادیر خیلی بزرگ (مثلاً > 1e9) احتمالاً ریال هستند.
df["price_toman"] = df["price"] // 10

# محاسبه price per m2 (تومان)
df["price_per_m2"] = df["price_toman"] / df["size"]

# اگر ستون neighborhood فارسی/انگلیسی متنوع است، سعی می‌کنیم نرمال‌سازی ساده انجام دهیم
df["neighborhood"] = df["neighborhood"].astype(str).str.strip()

# گروه‌بندی بر اساس محله و محاسبه آمار
grouped = df.groupby("neighborhood")["price_per_m2"]

stats = {}
for neigh, grp in grouped:
    arr = grp.dropna().values
    if len(arr) == 0:
        continue
    stats[neigh] = {
        "count": int(len(arr)),
        "mean": float(grp.mean()),
        "median": float(grp.median()),
        "min": float(grp.min()),
        "max": float(grp.max()),
        "std": float(grp.std(ddof=0))
    }

# ذخیره آمار به JSON
with open(OUT_STATS, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print(f"✅ Neighborhood stats saved to {OUT_STATS}")
print("Sample stats (top 10):")
for i, (k,v) in enumerate(stats.items()):
    print(f"  {k}: count={v['count']}, median={v['median']:.0f} T/m²")
    if i >= 9:
        break
