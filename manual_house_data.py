# manual_house_data.py
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------
# راه‌اندازی ChromeDriver
# ---------------------------
def init_driver(headless=False):
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    if headless:
        options.add_argument("--headless=new")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

# ---------------------------
# تبدیل متن قیمت به عدد (ریال)
# ---------------------------
def parse_price(text):
    if not text:
        return None
    t = re.sub(r"[^\d]", "", text)
    if not t:
        return None
    try:
        val = int(t)
        if val < 10_000_000:  # احتمالاً تومان
            return val * 10
        return val
    except:
        return None

# ---------------------------
# تبدیل متن متراژ به عدد
# ---------------------------
def parse_size(text):
    if not text:
        return None
    m = re.search(r"(\d{2,4})\s*(?:متر|m|m²|متری)", text)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    m2 = re.search(r"\b(\d{2,4})\b", text)
    if m2:
        val = int(m2.group(1))
        if 20 <= val <= 2000:
            return val
    return None

# ---------------------------
# استخراج اطلاعات از یک بلوک HTML
# ---------------------------
def extract_from_block(block):
    text = block.get_text(separator=" | ", strip=True)
    # قیمت
    price = None
    price_matches = re.findall(r"(\d{1,3}(?:[,\d]{3})*(?:\s*(?:تومان|ریال)?)?)", text)
    for p in price_matches:
        p_val = parse_price(p)
        if p_val and p_val > 10_000_000:
            price = p_val
            break
    # متراژ
    size = None
    m = re.search(r"(\d{2,4})\s*(?:متر|m|m²|متری)", text)
    if m:
        size = parse_size(m.group(0))
    # محله
    neighborhood = None
    possible_neighborhoods = [
        "بهشت","مخابرات","اندیشه","شهرک دانشگاه","انقلاب","شاهد","جمهوری","شهدا"
    ]
    for n in possible_neighborhoods:
        if n in text:
            neighborhood = n
            break
    if neighborhood is None:
        parts = text.split("|")
        if parts:
            candidate = parts[0].strip()
            if 2 <= len(candidate) <= 40:
                neighborhood = candidate
    return price, size, neighborhood

COMMON_SELECTORS = [
    'article',
    'li[role="listitem"]',
    'div[role="listitem"]',
    'div[class*="post-card"]',
    'div[class*="kt-post-card"]',
    'div[class*="product"]',
    'div[class*="card"]',
    'div[class*="advert"]',
    'div[class*="listing"]',
    'div[class*="item"]',
]

# ---------------------------
# اسکرپ سایت‌ها
# ---------------------------
def scrape_site(driver, url, max_scroll=5, wait_sec=2):
    try:
        driver.get(url)
    except WebDriverException as e:
        print("⚠️ Warning: driver.get timeout/err:", e)
    time.sleep(wait_sec)
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_sec)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    soup = BeautifulSoup(driver.page_source, "html.parser")
    blocks = []
    for sel in COMMON_SELECTORS:
        found = soup.select(sel)
        if found:
            blocks.extend(found)
    if not blocks:
        blocks = soup.find_all("div")[:500]
    return blocks

# ---------------------------
# اسکرپ کل سایت‌ها
# ---------------------------
def scrape_all(headless=False):
    driver = init_driver(headless=headless)
    sites = [
        {"name": "ariamarz", "url": "https://www.ariamarz.com/buy-apartment/borujerd"},
        {"name": "divar", "url": "https://divar.ir/s/borujerd/buy-residential"},
        {"name": "sheypoor", "url": "https://www.sheypoor.com/s/borujerd/houses-apartments-for-sale"}
    ]
    rows = []
    try:
        for site in sites:
            print("🔹 Extracting from", site["name"], "...")
            blocks = scrape_site(driver, site["url"], max_scroll=10, wait_sec=2)
            cnt = 0
            for b in blocks:
                price, size, neighborhood = extract_from_block(b)
                if price is not None or size is not None:
                    rows.append({
                        "price": price,
                        "size": size,
                        "neighborhood": neighborhood
                    })
                    cnt += 1
            print(f"  ~{cnt} candidate records found in {site['name']}")
    finally:
        driver.quit()

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["price", "size"], how="all").reset_index(drop=True)

    if df.empty:
        print("⚠️ No scraped data — using fallback sample data.")
        df = pd.DataFrame([
            {"price": 1_500_000_000, "size": 120, "neighborhood": "بهشت"},
            {"price": 1_200_000_000, "size": 100, "neighborhood": "مخابرات"},
            {"price": 1_000_000_000, "size": 90,  "neighborhood": "اندیشه"},
        ])

    df.to_csv("manual_house_data.csv", index=False, encoding="utf-8-sig")
    print("✅ Scraping complete — manual_house_data.csv saved. Total rows:", len(df))
    return df

# ---------------------------
# اجرای کد
# ---------------------------
if __name__ == "__main__":
    df = scrape_all(headless=False)  # برای تست اول headless=False باشه
    print(df.head())
