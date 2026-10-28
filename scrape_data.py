import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# تنظیمات Selenium
def init_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

# تبدیل متن به عدد
def parse_price(text):
    if not text: return None
    t = re.sub(r"[^\d]", "", text)
    if not t: return None
    val = int(t)
    return val*10 if val < 10_000_000 else val  # تومان -> ریال

def parse_size(text):
    if not text: return None
    m = re.search(r"(\d{2,4})", text)
    if m:
        val = int(m.group(1))
        if 20 <= val <= 2000:
            return val
    return None

def extract_from_block(block):
    text = block.get_text(separator=" | ", strip=True)
    price_matches = re.findall(r"\d{1,3}(?:[,\d]{3})*", text)
    price = None
    for p in price_matches:
        price = parse_price(p)
        if price: break
    size = parse_size(text)
    neighborhood_list = ["Behesht","Mokhaberat","Andisheh","ShahrakDaneshgah",
                         "Enghelab","Shahed","Jomhouri","Shohada",
                         "بهشت","مخابرات","اندیشه","شهرک دانشگاه","انقلاب","شاهد","جمهوری","شهدا"]
    neighborhood = next((n for n in neighborhood_list if n in text), None)
    return price, size, neighborhood

COMMON_SELECTORS = [
    'article','li[role="listitem"]','div[role="listitem"]',
    'div[class*="post-card"]','div[class*="kt-post-card"]','div[class*="product"]',
    'div[class*="card"]','div[class*="advert"]','div[class*="listing"]','div[class*="item"]'
]

def scrape_site(driver, url, max_scroll=3, wait_sec=2):
    try: driver.get(url)
    except Exception as e: print("Warning:", e)
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_sec)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height: break
        last_height = new_height
    soup = BeautifulSoup(driver.page_source, "html.parser")
    blocks = []
    for sel in COMMON_SELECTORS:
        blocks.extend(soup.select(sel))
    if not blocks: blocks = soup.find_all("div")[:500]
    return blocks

def scrape_all(headless=True):
    driver = init_driver(headless=headless)
    sites = [
        {"name":"ariamarz","url":"https://www.ariamarz.com/buy-apartment/borujerd"},
        {"name":"divar_res","url":"https://divar.ir/s/borujerd/buy-residential"},
        {"name":"divar_apt","url":"https://divar.ir/s/borujerd/buy-apartment"},
        {"name":"sheypoor","url":"https://www.sheypoor.com/s/borujerd/houses-apartments-for-sale"}
    ]
    rows=[]
    try:
        for site in sites:
            print("Extracting:", site["name"])
            blocks = scrape_site(driver, site["url"], max_scroll=5)
            for b in blocks:
                price, size, neighborhood = extract_from_block(b)
                if price or size:
                    rows.append({"site":site["name"],"price":price,"size":size,"neighborhood":neighborhood})
    finally: driver.quit()
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["price","size"], how="all").reset_index(drop=True)
    df.to_csv("manual_house_data.csv", index=False, encoding="utf-8-sig")
    print("Saved manual_house_data.csv with", len(df), "rows")
    return df

if __name__=="__main__":
    scrape_all()
